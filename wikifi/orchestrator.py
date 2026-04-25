from pathlib import Path
from typing import List, Optional
from loguru import logger
from wikifi.config import settings
from wikifi.models import ExecutionSummary, ExtractionNote, IntrospectionAssessment
from wikifi.walker import RepoWalker
from wikifi.workspace import WorkspaceManager
from wikifi.extraction import Introspector, Extractor
from wikifi.synthesis import Synthesizer
from wikifi.derivation import Deriver
from wikifi.provider.factory import get_provider

class Orchestrator:
    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir).resolve()
        self.workspace = WorkspaceManager(str(self.target_dir))
        self.walker = RepoWalker(str(self.target_dir))
        self.provider = get_provider()
        self.summary = ExecutionSummary()

    async def init_workspace(self):
        logger.info("Initializing workspace...")
        self.workspace.initialize()
        self.summary.stages_completed.append("Initialization")

    async def run_introspection(self) -> IntrospectionAssessment:
        logger.info("Starting introspection...")
        files = self.walker.walk()
        dir_summary = self.walker.summarize(files)
        
        introspector = Introspector(self.provider)
        assessment = await introspector.assess(dir_summary)
        
        self.workspace.save_introspection(assessment)
        self.summary.stages_completed.append("Introspection")
        return assessment

    async def run_extraction(self) -> List[ExtractionNote]:
        logger.info("Starting extraction...")
        files = self.walker.walk()
        extractor = Extractor(self.provider, self.target_dir)
        
        notes = []
        for f in files:
            logger.debug(f"Extracting from {f.relative_to(self.target_dir)}")
            note = await extractor.extract_note(f)
            if note:
                self.workspace.save_note(note)
                notes.append(note)
        
        self.summary.stages_completed.append("Extraction")
        return notes

    async def run_synthesis(self, assessment: IntrospectionAssessment, notes: List[ExtractionNote]):
        logger.info("Starting synthesis...")
        synthesizer = Synthesizer(self.provider)
        primary_content = {}
        
        for section in synthesizer.sections:
            logger.info(f"Synthesizing {section}...")
            content = await synthesizer.synthesize_section(section, assessment, notes)
            self.workspace.save_section(section.lower().replace(" ", "_"), content)
            primary_content[section] = content
            
        self.summary.stages_completed.append("Synthesis")
        return primary_content

    async def run_derivation(self, assessment: IntrospectionAssessment, primary_content: dict):
        logger.info("Starting derivation...")
        deriver = Deriver(self.provider)
        
        for section in deriver.derivative_sections:
            logger.info(f"Deriving {section}...")
            content = await deriver.derive_section(section, assessment, primary_content)
            self.workspace.save_section(section.lower().replace(" ", "_"), content)
            
        self.summary.stages_completed.append("Derivation")

    async def walk(self):
        try:
            await self.init_workspace()
            assessment = await self.run_introspection()
            notes = await self.run_extraction()
            primary_content = await self.run_synthesis(assessment, notes)
            await self.run_derivation(assessment, primary_content)
            
            self.summary.success = True
            self.summary.message = "Wiki generation completed successfully."
        except Exception as e:
            logger.exception("Pipeline failed")
            self.summary.success = False
            self.summary.message = str(e)
        finally:
            import datetime
            self.summary.end_time = datetime.datetime.now()
            logger.info(f"Execution Summary: {self.summary.model_dump_json(indent=2)}")
            return self.summary

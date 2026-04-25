import pytest
from wikifi.orchestrator import Orchestrator
from unittest.mock import patch

@pytest.mark.asyncio
async def test_orchestrator_walk(tmp_path, mock_provider):
    # Setup tmp repo
    main_py = tmp_path / "main.py"
    main_py.write_text("print('hello world')\n" * 10)
    
    with patch("wikifi.orchestrator.get_provider", return_value=mock_provider):
        orchestrator = Orchestrator(str(tmp_path))
        summary = await orchestrator.walk()
        
        assert summary.success
        assert "Initialization" in summary.stages_completed
        assert "Introspection" in summary.stages_completed
        assert "Extraction" in summary.stages_completed
        assert "Synthesis" in summary.stages_completed
        assert "Derivation" in summary.stages_completed
        
        wiki_dir = tmp_path / ".wikifi"
        assert wiki_dir.exists()
        assert (wiki_dir / "introspection.json").exists()
        assert (wiki_dir / "notes").exists()
        assert len(list((wiki_dir / "notes").glob("*.json"))) == 1
        assert (wiki_dir / "sections").exists()
        assert len(list((wiki_dir / "sections").glob("*.md"))) > 0

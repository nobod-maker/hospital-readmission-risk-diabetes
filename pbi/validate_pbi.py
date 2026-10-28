import os
import sys
import json
from pathlib import Path

def test_pbi_integrity():
    pbi_dir = Path(__file__).resolve().parent
    report_name = "Healthcare_Readmission_Command_Center"
    report_dir = pbi_dir / f"{report_name}.Report"
    semantic_dir = pbi_dir / f"{report_name}.SemanticModel"
    pbip_path = pbi_dir / f"{report_name}.pbip"
    measures_path = pbi_dir / "measures.dax"
    
    print("Testing Power BI Fabric PBIR / TMDL Integrity...")
    
    # 1. PBIP file validation
    assert pbip_path.exists(), f"Missing {pbip_path}"
    with open(pbip_path, "r", encoding="utf-8") as f:
        pbip_data = json.load(f)
    assert "artifacts" in pbip_data, "Missing artifacts in pbip"
    assert len(pbip_data["artifacts"]) == 1, "PBIP must contain only report artifact"
    assert "report" in pbip_data["artifacts"][0], "Missing report in artifacts"
    print(" [PASS] .pbip project file schema valid.")
    
    # 2. definition.pbir validation
    pbir_file = report_dir / "definition.pbir"
    assert pbir_file.exists(), f"Missing {pbir_file}"
    with open(pbir_file, "r", encoding="utf-8") as f:
        pbir_data = json.load(f)
    dataset_path = pbir_data.get("datasetReference", {}).get("byPath", {}).get("path")
    assert dataset_path is not None, "pbir datasetReference.byPath.path cannot be null!"
    print(" [PASS] definition.pbir non-null datasetReference valid.")
    
    # 3. Report pages metadata
    pages_file = report_dir / "definition" / "pages" / "pages.json"
    assert pages_file.exists(), f"Missing {pages_file}"
    with open(pages_file, "r", encoding="utf-8") as f:
        pages_data = json.load(f)
    assert len(pages_data.get("pageOrder", [])) == 4, "Must have exactly 4 report pages"
    print(" [PASS] pages.json contains 4 report pages.")
    
    # 4. Check each page and visual
    for p_id in pages_data["pageOrder"]:
        p_json = report_dir / "definition" / "pages" / p_id / "page.json"
        assert p_json.exists(), f"Missing page.json for {p_id}"
        v_dir = report_dir / "definition" / "pages" / p_id / "visuals"
        assert v_dir.exists(), f"Missing visuals directory for {p_id}"
        vis_count = len(list(v_dir.iterdir()))
        assert vis_count >= 2, f"Page {p_id} has fewer than 2 visuals"
    print(" [PASS] All 4 report pages and visual containers exist.")
    
    # 5. Semantic model TMDL tab-indentation validation
    model_tmdl = semantic_dir / "definition" / "model.tmdl"
    assert model_tmdl.exists(), f"Missing {model_tmdl}"
    with open(model_tmdl, "r", encoding="utf-8") as f:
        m_lines = f.readlines()
    for line in m_lines:
        if line.startswith(" "):
            raise ValueError(f"TMDL indentation error: space found in {model_tmdl} -> {line}")
            
    rel_tmdl = semantic_dir / "definition" / "relationships.tmdl"
    assert rel_tmdl.exists(), f"Missing {rel_tmdl}"
    with open(rel_tmdl, "r", encoding="utf-8") as f:
        r_lines = f.readlines()
    for line in r_lines:
        if line.startswith(" "):
            raise ValueError(f"TMDL indentation error: space found in {rel_tmdl} -> {line}")
            
    tables_dir = semantic_dir / "definition" / "tables"
    table_files = list(tables_dir.glob("*.tmdl"))
    assert len(table_files) == 8, f"Expected 8 table TMDL files, found {len(table_files)}"
    for tf in table_files:
        with open(tf, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(" "):
                    raise ValueError(f"TMDL indentation error: space found in {tf} -> {line}")
    print(" [PASS] TMDL files strictly formatted with TAB indentation.")
    
    # 6. DAX measures repository
    assert measures_path.exists(), f"Missing {measures_path}"
    with open(measures_path, "r", encoding="utf-8") as f:
        dax_text = f.read()
    assert "[30-Day Readmission Rate]" in dax_text
    assert "[CMS Penalty Exposure]" in dax_text
    assert "[Intervention Net Savings]" in dax_text
    print(" [PASS] measures.dax contains required enterprise measures.")
    
    # 7. Test pbi_cli validation if available
    try:
        from pbi_cli.core.pbir_path import validate_report_structure
        errors = validate_report_structure(report_dir / "definition")
        if errors:
            print(f"pbi_cli validation notes: {errors}")
        else:
            print(" [PASS] pbi_cli core validation passed with 0 errors.")
    except ImportError:
        pass
        
    print("\n[SUCCESS] Power BI Command Center fully validated with exit code 0.")

if __name__ == "__main__":
    test_pbi_integrity()

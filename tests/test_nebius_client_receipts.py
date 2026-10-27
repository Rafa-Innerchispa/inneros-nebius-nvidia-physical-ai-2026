import sys,json
from pathlib import Path
from unittest import mock
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from nebius_client import NebiusNvidiaReasoning

@pytest.mark.parametrize("content,finish",[(None,"length"),(None,"stop"),("not-json","stop"),("[]","stop")])
def test_invalid_diagnosis_preserves_provider_usage_without_paid_retry(content,finish):
    reply={"id":"offline-response", "usage":{"completion_tokens":512},"choices":[{"finish_reason":finish,"message":{"content":content}}]}
    with mock.patch("urllib.request.urlopen") as http:
        http.return_value.__enter__.return_value.read.return_value=json.dumps(reply).encode()
        result=NebiusNvidiaReasoning(api_key="offline-key",model="nvidia/test").diagnose({"device_ref":"lab"})
    assert http.call_count==1
    assert result["inference_mode"]=="LOCAL_HEURISTIC"
    assert result["provider_receipt"]["evidence_mode"]=="BLOCKED"
    assert result["provider_receipt"]["response_id"]=="offline-response"
    assert result["provider_receipt"]["usage"]["completion_tokens"]==512
    assert json.loads(http.call_args.args[0].data)["max_tokens"]==2048
    assert "offline-key" not in json.dumps(result)

def test_output_budget_cannot_exceed_authorized_bound():
    with pytest.raises(ValueError):NebiusNvidiaReasoning(max_output_tokens=2049)

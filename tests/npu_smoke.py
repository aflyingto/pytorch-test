import pytest


def _require_torch():
    return pytest.importorskip("torch")


def _require_torch_npu():
    try:
        import torch_npu  # noqa: F401
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"torch_npu import failed: {exc}")


@pytest.mark.smoke
def test_npu_available():
    torch = _require_torch()
    _require_torch_npu()
    assert hasattr(torch, "npu"), "torch.npu missing"
    assert torch.npu.is_available(), "NPU device unavailable"


@pytest.mark.smoke
def test_npu_matmul_backward():
    torch = _require_torch()
    _require_torch_npu()
    if not torch.npu.is_available():
        pytest.skip("NPU unavailable")

    x = torch.randn(8, 8, device="npu", requires_grad=True)
    y = torch.randn(8, 8, device="npu")
    loss = (x @ y).pow(2).mean()
    loss.backward()

    assert x.grad is not None
    assert torch.isfinite(x.grad).all().item()

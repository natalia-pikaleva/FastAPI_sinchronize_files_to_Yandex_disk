import httpx
import pytest

@pytest.mark.asyncio
async def test_sync_endpoint():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get("/sync")
    assert response.status_code == 200
    data = response.json()
    assert "uploaded" in data
    assert "updated" in data
    assert "deleted" in data

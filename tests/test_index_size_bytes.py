from core.runtime_state import get_index_size_bytes
from core.config import DEFAULT_TSU_DATASET_PATH


def test_index_size_counts_tsu_dataset(tmp_path):
    assert get_index_size_bytes(tmp_path) == 0
    p = tmp_path / DEFAULT_TSU_DATASET_PATH
    p.parent.mkdir(parents=True)
    p.write_bytes(b"x" * 100)
    assert get_index_size_bytes(tmp_path) == 100

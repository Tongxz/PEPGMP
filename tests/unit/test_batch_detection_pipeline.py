import numpy as np
import pytest

from src.core.batch_detection_pipeline import BatchDetectionPipeline


class MockHumanDetector:
    def detect(self, image, **kwargs):
        return []

    def detect_batch(self, images, batch_size=None, **kwargs):
        return [[] for _ in images]


@pytest.mark.unit
class TestBatchDetectionPipeline:
    def test_records_actual_batch_count(self):
        pipeline = BatchDetectionPipeline(
            human_detector=MockHumanDetector(),
            hairnet_detector=None,
            behavior_recognizer=None,
            enable_batch_processing=True,
            max_batch_size=4,
        )

        frames = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(10)]
        results = pipeline.detect_batch(frames, batch_size=4)

        assert len(results) == 10

        stats = pipeline.get_batch_stats()
        assert stats["total_batches"] == 3
        assert stats["min_batch_size"] == 2
        assert stats["max_batch_size"] == 4

    def test_batch_processing_stats_attached_to_results(self):
        pipeline = BatchDetectionPipeline(
            human_detector=MockHumanDetector(),
            hairnet_detector=None,
            behavior_recognizer=None,
            enable_batch_processing=True,
            max_batch_size=8,
        )

        frames = [np.zeros((32, 32, 3), dtype=np.uint8) for _ in range(2)]
        results = pipeline.detect_batch(frames)

        assert len(results) == 2
        for result in results:
            assert result.processing_stats is not None
            assert "person_detection" in result.processing_stats
            assert "hairnet_detection" in result.processing_stats
            assert "behavior_detection" in result.processing_stats
            assert "assembly" in result.processing_stats
            assert "total" in result.processing_stats
            assert result.processing_stats["total"] >= 0

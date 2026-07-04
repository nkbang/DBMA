from core.utils import calculate_noise_score


class TestCalculateNoiseScore:
    def test_empty_text_returns_high_noise(self):
        result = calculate_noise_score("", file_type="txt")
        assert result["score"] == 100.0
        assert result["mode"] == "empty"

    def test_whitespace_only_returns_high_noise(self):
        result = calculate_noise_score("   \n\t  ", file_type="md")
        assert result["score"] == 100.0
        assert result["mode"] == "empty"

    def test_clean_plain_text_does_not_become_zero(self):
        text = "This is a clean sentence. This is another clean sentence."
        result = calculate_noise_score(text, file_type="txt")
        assert result["score"] >= 3.0
        assert result["mode"] == "plain_text"

    def test_pdf_ocr_text_scores_higher_than_clean_text(self):
        noisy = "T he 1\n2\npage 3\nm em bers"
        result = calculate_noise_score(noisy, file_type="pdf", is_ocr=True)
        assert result["mode"] == "pdf_ocr"
        assert result["score"] > 0

    def test_score_is_always_bounded(self):
        texts = ["", "plain text", "!!!!! #### ???", "T he m em bers page 12"]
        for t in texts:
            result = calculate_noise_score(t, file_type="txt")
            assert 0 <= result["score"] <= 100

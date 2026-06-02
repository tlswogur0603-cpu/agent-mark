from app.schemas.response import StructuredResult


class MarkdownFormatter:
    """
    StructuredResult -> Markdown 변환기.

    - 특정 포트/프레임워크에 묶이지 않는 순수 포매터로 유지한다.
    - 필요하면 Infrastructure 레벨에서 FormatterPort 어댑터가 이 클래스를 감싸서 사용한다.
    """

    def format(self, result: StructuredResult) -> str:
        parts: list[str] = [f"# 요약\n\n{result.summary or '내용 없음'}".strip()]

        parts.append("## 주요 키워드\n\n" + self._bullets(result.keywords))

        if result.action_points:
            parts.append("## 행동 포인트\n\n" + self._bullets(result.action_points))
        else:
            parts.append("## 행동 포인트\n\n없음")

        return "\n\n".join(parts).strip() + "\n"

    @staticmethod
    def _bullets(items: list[str]) -> str:
        if not items:
            return "없음"
        return "\n".join(f"- {item}" for item in items)

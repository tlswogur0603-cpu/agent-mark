from __future__ import annotations
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from app.ports.llm_port import LLMPort
from app.schemas.response import StructuredResult


class LangChainLLMAdapter(LLMPort):
    """LangChain 기반 Gemini LLM 어댑터 (Single-shot 구조화)."""

    def __init__(self, api_key: str, model_name: str) -> None:
        self._api_key = api_key
        self._model_name = model_name

        # langchain-google-genai의 생성자 파라미터 명이 버전별로 달라질 수 있어 방어적으로 처리한다.
        try:
            self._llm = ChatGoogleGenerativeAI(
                model=self._model_name,
                google_api_key=self._api_key,
                temperature=0,
            )
        except TypeError:
            self._llm = ChatGoogleGenerativeAI(  # type: ignore[call-arg]
                model=self._model_name,
                api_key=self._api_key,
                temperature=0,
            )

        # Pydantic 모델 기반 구조화 출력 강제
        self._structured_llm = self._llm.with_structured_output(StructuredResult)

    async def extract_structured(self, text: str, prompt: str) -> StructuredResult:
        """
        prompt와 text를 입력으로 받아 StructuredResult를 반환한다.
        - Single-shot: 한 번의 LLM 호출로 summary/keywords/action_points를 동시 생성
        - 비동기 I/O: ainvoke 사용
        """

        # 모델/버전별로 messages(list[BaseMessage]) 또는 str 입력을 허용한다.
        # 가장 호환성이 높은 방식으로 prompt + 원문을 단일 문자열로 구성한다.
        payload = (
            f"{prompt}\n\n"
            "----\n"
            "INPUT_TEXT:\n"
            f"{text}\n"
            "----\n"
        )

        result: Any = await self._structured_llm.ainvoke(payload)
        if isinstance(result, StructuredResult):
            return result

        # with_structured_output이 dict를 반환하는 구현도 있어 마지막으로 검증/변환한다.
        return StructuredResult.model_validate(result)

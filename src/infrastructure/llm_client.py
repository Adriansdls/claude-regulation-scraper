"""LLM client abstraction supporting multiple providers."""

import json
from typing import Optional, Dict, Any, List
from anthropic import Anthropic
from openai import OpenAI

from .config import get_config


class LLMClient:
    """Unified LLM client supporting Anthropic and OpenAI."""

    def __init__(self, provider: Optional[str] = None):
        """Initialize LLM client.

        Args:
            provider: "anthropic" or "openai". If None, uses config default.
        """
        self.config = get_config()
        self.provider = provider or self.config.default_llm

        if self.provider == "anthropic":
            if not self.config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.client = Anthropic(api_key=self.config.anthropic_api_key)
            self.model = self.config.anthropic_model
        elif self.provider == "openai":
            if not self.config.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=self.config.openai_api_key)
            self.model = self.config.openai_model
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> str:
        """Get completion from LLM.

        Args:
            prompt: User prompt
            system: System prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            json_mode: Whether to request JSON output

        Returns:
            Response text
        """
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature or self.config.temperature

        if self.provider == "anthropic":
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        elif self.provider == "openai":
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content

    async def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Get JSON completion from LLM.

        Args:
            prompt: User prompt (should request JSON output)
            system: System prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Parsed JSON response
        """
        # Add JSON instruction to prompt if not present
        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nReturn your response as valid JSON."

        response = await self.complete(
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
        )

        # Try to parse JSON
        try:
            # Find JSON in response (sometimes wrapped in markdown)
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}\n\nResponse: {response}")

    async def batch_complete(
        self,
        prompts: List[str],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> List[str]:
        """Get completions for multiple prompts.

        Args:
            prompts: List of user prompts
            system: System prompt (same for all)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            List of response texts
        """
        # For now, sequential (can optimize with asyncio.gather later)
        results = []
        for prompt in prompts:
            result = await self.complete(
                prompt=prompt, system=system, max_tokens=max_tokens, temperature=temperature
            )
            results.append(result)
        return results


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """Get global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(provider=provider)
    return _llm_client

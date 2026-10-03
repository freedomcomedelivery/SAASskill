from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .capabilities import CAPABILITY_FALLBACKS, DEFAULT_PROVIDER_ORDER, PROVIDER_CAPABILITIES


@dataclass(frozen=True, slots=True)
class ProviderRoute:
    requested_capability: str
    effective_capability: str
    provider: str | None
    degraded: bool
    reason: str

    @property
    def resolved(self) -> bool:
        return self.provider is not None

    def to_dict(self) -> dict:
        return {
            "requested_capability": self.requested_capability,
            "effective_capability": self.effective_capability,
            "provider": self.provider,
            "degraded": self.degraded,
            "reason": self.reason,
            "resolved": self.resolved,
        }


class ProviderRouter:
    """Resolve logical capabilities to providers available in the current host."""

    def __init__(
        self,
        available_providers: Iterable[str] = (),
        preferences: dict[str, list[str]] | None = None,
    ) -> None:
        self.available = set(available_providers)
        self.preferences = preferences or {}

    def _providers_for(self, capability: str, candidates: list[str] | None = None) -> list[str]:
        preferred = self.preferences.get(capability) or DEFAULT_PROVIDER_ORDER.get(capability, [])
        if not candidates:
            return list(preferred)
        candidate_set = set(candidates)
        ordered = [p for p in preferred if p in candidate_set]
        ordered.extend(p for p in candidates if p not in ordered)
        return ordered

    def _resolve_exact(self, capability: str, candidates: list[str] | None = None) -> str | None:
        for provider in self._providers_for(capability, candidates):
            if provider not in self.available:
                continue
            if capability in PROVIDER_CAPABILITIES.get(provider, set()):
                return provider
        return None

    def resolve(self, capability: str, candidates: list[str] | None = None) -> ProviderRoute:
        provider = self._resolve_exact(capability, candidates)
        if provider:
            return ProviderRoute(
                requested_capability=capability,
                effective_capability=capability,
                provider=provider,
                degraded=False,
                reason=f"Resolved exact capability through {provider}.",
            )

        for fallback in CAPABILITY_FALLBACKS.get(capability, []):
            provider = self._resolve_exact(fallback, candidates)
            if provider:
                return ProviderRoute(
                    requested_capability=capability,
                    effective_capability=fallback,
                    provider=provider,
                    degraded=True,
                    reason=f"No exact provider available; degraded fallback to {fallback} via {provider}.",
                )

        suffix = f" within candidates {candidates}" if candidates else ""
        return ProviderRoute(
            requested_capability=capability,
            effective_capability=capability,
            provider=None,
            degraded=False,
            reason=f"No available provider can satisfy this capability{suffix}.",
        )

    def matrix(self) -> dict[str, dict]:
        capabilities = set(DEFAULT_PROVIDER_ORDER)
        capabilities.update(CAPABILITY_FALLBACKS)
        return {cap: self.resolve(cap).to_dict() for cap in sorted(capabilities)}

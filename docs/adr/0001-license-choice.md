# ADR-0001: AGPL-3.0 License Choice

## Status

Accepted (2026-07)

## Context

SKPL Agent is a fusion of four upstream open-source projects:

1. **AgentScope** — Licensed under Apache 2.0
2. **OpenWolf** — Licensed under MIT
3. **Agent-S** — Licensed under MIT
4. **Firecrawl** — Licensed under AGPL-3.0

We need to choose a license for SKPL Agent that is compatible with all four
upstream licenses while supporting the project's goals.

## Decision

We chose **GNU Affero General Public License v3.0 (AGPL-3.0)** for SKPL Agent.

## Rationale

### Compatibility

AGPL-3.0 is compatible with all four upstream licenses:

| Upstream | License | Compatible with AGPL-3.0? |
|----------|---------|--------------------------|
| AgentScope | Apache 2.0 | Yes — Apache 2.0 is compatible with GPLv3/AGPLv3 |
| OpenWolf | MIT | Yes — MIT is compatible with all GPL licenses |
| Agent-S | MIT | Yes — MIT is compatible with all GPL licenses |
| Firecrawl | AGPL-3.0 | Yes — Same license, no compatibility issue |

### Network Copyleft

AGPL-3.0 is a strong copyleft license that extends GPLv3 to cover network
use. This is important for SKPL Agent because:

1. **Service Model**: SKPL Agent is primarily deployed as a network service
   (SaaS). AGPL ensures that if someone modifies SKPL Agent and offers it as
   a service, they must share their modifications.

2. **Ecosystem Fairness**: It prevents large corporations from taking the
   open-source code, adding proprietary enhancements, and offering a
   competing service without contributing back.

3. **Upstream Alignment**: Firecrawl, one of the four upstream projects,
   already uses AGPL-3.0. Using the same license simplifies compliance.

### Alternatives Considered

#### Apache 2.0

- **Pros**: Permissive, widely adopted, compatible with all upstream licenses
- **Cons**: No network copyleft protection. Cloud providers could offer
  proprietary hosted versions without contributing back.

#### MIT

- **Pros**: Most permissive, simplest compliance
- **Cons**: No copyleft at all. No protection against proprietary forks.

#### GPL-3.0

- **Pros**: Strong copyleft for distributed software
- **Cons**: Does not cover network use (the "ASP loophole"). SKPL Agent is
  primarily a network service, so GPL-3.0 would not provide meaningful
  copyleft protection.

#### Business Source License (BSL)

- **Pros**: Time-delayed open source, commercial protection
- **Cons**: Not truly open source during the restriction period. Incompatible
  with the open-source philosophy of the upstream projects.

### Why Not a More Permissive License?

While permissive licenses like MIT or Apache 2.0 would make adoption easier,
they would not protect the project's long-term sustainability:

1. The project is a fusion of four upstream projects, three of which use
   permissive licenses. AGPL-3.0 ensures that the fusion itself remains
   open.

2. The project includes significant original work (context management
   integration, desktop automation orchestration, multi-tenant quotas,
   update tracking) that adds value beyond the upstream components.

3. The AGPL-3.0 copyleft applies only to the SKPL Agent codebase, not to
   applications built on top of it (agents, tools, and skills created by
   users are their own intellectual property).

## Consequences

### Positive

- **Ecosystem Protection**: Prevents proprietary forks of the fusion platform
- **Contribution Incentive**: Organizations using SKPL Agent as a service
  must contribute improvements back
- **Upstream Alignment**: Consistent with Firecrawl's license choice
- **Legal Clarity**: AGPL-3.0 is well-understood and widely used

### Negative

- **Adoption Barrier**: Some organizations have policies against AGPL-3.0
  software due to copyleft concerns
- **Compliance Complexity**: AGPL-3.0 compliance is more complex than
  permissive licenses
- **Dual Licensing Requests**: Some users may request alternative licensing
  for commercial use
- **Perceived Risk**: Legal teams unfamiliar with AGPL-3.0 may flag it
  during procurement

### Mitigations

1. **Clear Documentation**: We provide a `LICENSE` file and license headers
   in all source files.

2. **Dual Licensing Option**: We may offer a commercial license for
   organizations that cannot use AGPL-3.0.

3. **Contribution Guide**: Our `CONTRIBUTING.md` will clarify that user
   contributions are under AGPL-3.0.

4. **Boundary Clarity**: We will document what constitutes a "derivative
   work" under AGPL-3.0 (the SKPL Agent platform itself) versus user
   content (agents, tools, skills, configurations).

## References

- [GNU AGPL-3.0 Full Text](https://www.gnu.org/licenses/agpl-3.0.html)
- [Apache 2.0 Compatibility with GPLv3](https://www.apache.org/licenses/GPL-compatibility.html)
- [Firecrawl AGPL-3.0 License](https://github.com/mendableai/firecrawl/blob/main/LICENSE)
- [FSF: Why AGPL](https://www.gnu.org/licenses/why-affero-gpl.html)
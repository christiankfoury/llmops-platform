# Application screenshots

These are actual local browser captures of the production-built Next.js application,
using fixed invented fixtures. The default demo contains 12 requests across three
application scopes, including three failures and corresponding configuration records.
No backend, database, identity provider or paid LLM service supplies the example data.

## Overview

![Application overview with synthetic usage and request records](assets/screenshots/dashboard-overview.jpg)

## Request details

![Synthetic request detail with latency, tokens and cost](assets/screenshots/request-detail.jpg)

## Failure filtering

![Dashboard filtered to failed synthetic requests](assets/screenshots/failure-filter.jpg)

The examples have fixed September 17, 2026 timestamps. Use **All time** to view the
whole fixture set; relative date filters can legitimately return no rows later.
Counts, averages and costs derive from the displayed fixture dataset, not actual
provider charges or the measured local recovery sample.

[Capture provenance](assets/screenshots/publication-capture.json) records source
hashes, viewport and image hashes. [Original September 8 captures](assets/screenshots/phase-64.md)
remain as historical evidence. Neither gallery demonstrates Grafana or AWS operation.

## Reproduce

Start the default Compose stack and open the web dashboard. Confirm its
**Synthetic demo Â· Fixed example data Â· Read only** notice. Capture the overview,
open `demo-request-001`, then close the details and set Status to `failed`.
Use a 1440-pixel desktop viewport and preserve the notice. Inspect mobile layout
separately. Do not edit screenshot content or substitute generated images.

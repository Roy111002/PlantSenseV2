# Web dashboard — next milestone
The Flask/Jinja dashboard is implemented at `/dashboard`, with sensor cards,
history charts, latest image, AI assessment, and actuator states. Current readings
and output states come from `/api/plant/latest-data`, independently of the latest
AI result. It polls every ten seconds and marks reports older than two minutes
as stale. See [telemetry setup](../README-TELEMETRY.md) for simulation and wiring.

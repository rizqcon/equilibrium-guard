# Changelog

All notable changes to Equilibrium Guard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-01

### Added
- Initial release
- **Constraint Validator** — Define compliance rules as executable constraints
  - Three severity levels: ADVISORY, REQUIRED, MANDATORY
  - Decorator pattern (`@guarded`) for wrapping functions
  - Validation history for audit trails
- **Smart Anchor** — Risk-weighted autonomy system
  - Risk-weighted budget (safe ops free, risky ops cost more)
  - Dynamic trust score that builds/depletes based on behavior
  - Five drift detectors: escalating access, external drift, speed drift, repetition anomaly, warning accumulation
  - Tunable parameters via `AnchorParams`
- **Compliance Mappings** — Pre-built constraints for:
  - SOC 2 (CC6.1, CC6.2, CC6.3, CC7.2, C1.1)
  - HIPAA (164.312 access, audit, integrity, transmission; 164.502 minimum necessary)
  - CIS Controls (4.1, 5.1, 5.4, 8.2, 3.3)
  - RIZQ internal policies
- **EquilibriumGuard** — High-level integration class

### Attribution
Inspired by [S.I.S. (Sovereign Intelligence System)](https://github.com/Architect-SIS/sis-skill) by Kevin Fain.
Core concepts of equilibrium constraints and human anchoring adapted for compliance automation.

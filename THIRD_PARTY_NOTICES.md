# Third-party material and attribution

`custom_components/hive_ev/auth.py` uses and adapts authentication behaviour from **Pyhive / pyhive-integration 1.0.10**, including SRP/MFA setup, authentication-parameter construction and device confirmation. Pyhive is MIT licensed, copyright (c) 2020 Pyhive. The complete original notice is preserved in [licenses/Pyhive-MIT.txt](licenses/Pyhive-MIT.txt).

Source: [Pyhive/Pyhiveapi](https://github.com/Pyhive/Pyhiveapi). The runtime dependency remains pinned to the investigated version. Other installed dependencies retain their respective licences and are not vendored here.

The original project implementation and documentation were generated with OpenAI Codex, with human-run account/hardware validation as described in [provenance](docs/development-and-provenance.md). No human author identity or full human-review claim is fabricated.

Hive's official Android application was inspected locally to establish protocol behaviour. Its APKs, bytecode, decompiled files, images and other application assets are not included or licensed by this repository. Hive, Centrica, Alfen, Home Assistant and OpenAI names identify their respective products and do not imply endorsement.

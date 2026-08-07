# Changelog

## [0.2.2](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.2.1...v0.2.2) (2026-08-07)


### Features

* **status-stream:** reconnect a dropped push session with exponential backoff ([6121856](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/612185679f196c207600280ec2eda44b9b2f6e2c))


### Bug Fixes

* surface MQTT connection loss and stop leaking the session on failed start ([52c452a](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/52c452a750b0d6fe0896cd79896c1048e5c70d46))


### Code Refactoring

* derive the reported version from package metadata and drop dead code ([77092d2](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/77092d205faf2b0499b4eb13cc07e5de7a74be01))


### Dependencies

* **deps:** bump aiohttp from 3.13.5 to 3.14.3 ([0627655](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/06276550c4fcae3a74539480adcf42daf91d8e3b))
* **deps:** bump cryptography from 48.0.0 to 50.0.0 ([1c98147](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/1c98147b31da3fd79e231c9e19c92ae26a1142b2))


### Continuous Integration

* run checks on pull requests targeting any branch ([5c35327](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/5c35327fdc715bfeef21b33f35fc7b75c9a441cf))
* run code scanning on pull requests targeting any branch ([63916b5](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/63916b5782c42ebcd7977e951b4686e5b9283753))


### Miscellaneous Chores

* broaden the ruff rule set with pydocstyle, bandit, and async checks ([0f5d1b1](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/0f5d1b1dbafa5db5b7b92f87c059af0e65eae6f8))
* keep blind-except off for the stream's background supervisor ([b0dd1a2](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/b0dd1a24394f4906cf0a5d3c806f972de173d64b))
* lint the whole ruff rule set and name the protocol status codes ([e7d1612](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/e7d1612b96b78d100a1fe317d67ad964c3e4d663))
* move CI to the shared workflows repository ([7f93fce](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/7f93fce98a29a4c24e4490b225292395cb02b373))
* release on every conventional commit type ([2c05f1a](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/2c05f1a410a0eaa6e8e70231e91b3b0b48d4c514))

## [0.2.1](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.2.0...v0.2.1) (2026-08-02)


### Bug Fixes

* wrap request timeouts in TransportError ([e2ce24b](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/e2ce24b217405006890902287d3f07d86cf249fa))

## [0.2.0](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.12...v0.2.0) (2026-08-01)


### ⚠ BREAKING CHANGES

* `tls_insecure` is gone from `watch_status()`, `StatusStream` and `MqttTransport`. `ca_certs` and `tls_context` remain for callers that need to supply their own trust material.

### Features

* verify the MQTT broker's TLS chain ([a844b32](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/a844b3294326b2be8cc5645a10d261db0b47fdfc))


### Documentation

* update CLAUDE.md ([95f3755](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/95f3755a85d4a70feb3ffc1ddce59bd41f9198eb))

## [0.1.12](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.11...v0.1.12) (2026-07-10)


### Bug Fixes

* **mqtt:** bind to the account's resolved Aliyun region, not hardcoded us-east-1 ([f83d742](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/f83d74206a13fa5263e185eb43fbfeafa2d18bd4))

## [0.1.11](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.10...v0.1.11) (2026-06-23)


### Bug Fixes

* **client:** use regional aliyun gateway for iot calls ([4f41aca](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/4f41aca43d443d612edd16684195af69b916c20e))
* **client:** use regional aliyun gateway for iot calls ([7d1a4a2](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/7d1a4a29cfbc495ee726a9238ccc44253f361fc5))


### Documentation

* **changelog:** backfill EU + 3019 fixes under 0.1.10 ([9d9bc95](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/9d9bc95cd781788e7a639cd400b198def220d887))
* **changelog:** record EU cluster + 3019 fixes under 0.1.10 ([c6e7c14](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/c6e7c14e53fec19ec6916e99f55464cf2b4340d1))

## [0.1.10](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.9...v0.1.10) (2026-06-21)


### Bug Fixes

* **region:** point EU cluster to euapi.neakasa.com — `eu.neakasa.com` is the Shopify storefront and returned HTTP 404 on `/api/login`, blocking login for European users ([0fba072](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/0fba0720)) ([roquerodrigo/ha-neakasa-litterbox#32](https://github.com/roquerodrigo/ha-neakasa-litterbox/issues/32))
* **auth:** treat server code 3019 as invalid credentials (account not registered on the cluster) ([b9cbfc4](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/b9cbfc4e))


### Documentation

* fix stale CODE_STYLE.md references ([#24](https://github.com/roquerodrigo/neakasa-litterbox-sdk/issues/24)) ([f5c5f6f](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/f5c5f6f74a1d7acfa6e7203a62e4c8673e9cd0a4))

## [0.1.9](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.8...v0.1.9) (2026-06-01)


### Features

* **status:** map operating_state 5 -&gt; CAT_APPEARS + warn on unmapped codes ([f896e12](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/f896e121a4bca58eed43b0c8b93136bf7b7f0210))
* **status:** map operating_state 5 -&gt; OCCUPIED (cat inside) ([1b27837](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/1b2783749919f072aafa18a5498e3fabd158500f))

## [0.1.8](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.7...v0.1.8) (2026-06-01)


### Bug Fixes

* **build:** pin hatchling &lt;1.28 so the PyPI publish accepts the wheel ([64484f6](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/64484f60f0d3979ebfc9fb6e33e1d5ee2c02abf7))
* **build:** pin hatchling &lt;1.28 so the PyPI publish accepts the wheel ([b7606d4](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/b7606d42e4db435ab3830ae6f8e986b23b6d7f5a))

## [0.1.7](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.6...v0.1.7) (2026-06-01)


### Features

* **status:** expose operating_state (idle/cleaning/restoring/leveling) ([5a88871](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/5a8887135b066f08d72dd869c1c05d1a81f4b013))
* **status:** expose operating_state (idle/cleaning/restoring/leveling) ([8a3a98e](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/8a3a98eaa7f6a11f6e8223c950b09ea753bbbd78))

## [0.1.6](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.5...v0.1.6) (2026-05-31)


### Bug Fixes

* **status:** derive bucket_full from room_of_bin, not bucketStatus ([a6b3d93](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/a6b3d93a3bf906c1174d72e982640c101cdabd34))
* **status:** derive bucket_full from room_of_bin, not bucketStatus ([c6152b7](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/c6152b7550c47cd10238930505c320cb51f16a14))

## [0.1.5](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.4...v0.1.5) (2026-05-25)


### Documentation

* add CI and PyPI badges ([2073f1f](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/2073f1f2635d2a01cb590af0ba3b97c55a74c2d8))
* add CI and PyPI badges ([a32e9e7](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/a32e9e7ff4bb9c4291e28820a44a1a7f18b03fbd))

## [0.1.4](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.3...v0.1.4) (2026-05-23)


### Bug Fixes

* **client:** fall back to full REST re-login on handshake failure ([e758985](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/e7589854fe7b77b795604a52392dbb8d30476680))
* **client:** fall back to full REST re-login when Aliyun handshake fails ([838c323](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/838c32392cd865e7aa5a118366e24c57629d31db))

## [0.1.3](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.2...v0.1.3) (2026-05-22)


### Bug Fixes

* **aliyun:** auto-refresh iotToken on 401 instead of failing the call ([47b13ed](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/47b13ed1891a8246462ea60d390db7bd74ddc808))

## [0.1.2](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.1...v0.1.2) (2026-05-21)


### Bug Fixes

* **mqtt:** defer TLS context build to connect() to avoid blocking event loop ([ec9c823](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/ec9c8230132f17773127ff3773b1950d74922a0e))

## [0.1.1](https://github.com/roquerodrigo/neakasa-litterbox-sdk/compare/v0.1.0...v0.1.1) (2026-05-19)


### Features

* initial public release of neakasa-litterbox-sdk ([3b8baa0](https://github.com/roquerodrigo/neakasa-litterbox-sdk/commit/3b8baa09e18c4c27d68d0dd7d9ad62c45123676d))

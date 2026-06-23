# Changelog

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

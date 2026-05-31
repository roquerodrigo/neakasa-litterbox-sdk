# Changelog

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

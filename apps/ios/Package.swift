// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "OBSCameraPro",
    platforms: [
        .iOS(.v16)
    ],
    products: [
        .library(
            name: "OBSCameraCore",
            targets: ["OBSCameraCore"]
        ),
    ],
    dependencies: [
        // Official WebRTC iOS Framework
        .package(url: "https://github.com/stasel/WebRTC.git", from: "120.0.0")
    ],
    targets: [
        .target(
            name: "OBSCameraCore",
            dependencies: [
                .product(name: "WebRTC", package: "WebRTC")
            ],
            path: "OBSCamera/Sources"
        )
    ]
)


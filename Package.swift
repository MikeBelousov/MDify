// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "MDify",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "MDify", targets: ["MDify"]),
        .library(name: "MDifyCore", targets: ["MDifyCore"])
    ],
    targets: [
        .target(
            name: "MDifyCore"
        ),
        .executableTarget(
            name: "MDify",
            dependencies: ["MDifyCore"]
        ),
        .testTarget(
            name: "MDifyCoreTests",
            dependencies: ["MDifyCore"]
        )
    ]
)

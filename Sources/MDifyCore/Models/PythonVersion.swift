import Foundation

public struct PythonVersion: Comparable, CustomStringConvertible, Equatable, Sendable {
    public static let minimumSupported = PythonVersion(major: 3, minor: 10, patch: 0)
    public static let firstUnsupported = PythonVersion(major: 3, minor: 14, patch: 0)

    public let major: Int
    public let minor: Int
    public let patch: Int

    public init(major: Int, minor: Int, patch: Int) {
        self.major = major
        self.minor = minor
        self.patch = patch
    }

    public init?(_ output: String) {
        let versionToken = output
            .split(whereSeparator: { $0 == " " || $0 == "\n" || $0 == "\t" })
            .first(where: { token in
                token.split(separator: ".").count >= 2 && token.first?.isNumber == true
            })

        guard let versionToken else { return nil }
        let parts = versionToken.split(separator: ".").compactMap { Int($0) }
        guard parts.count >= 2 else { return nil }

        self.major = parts[0]
        self.minor = parts[1]
        self.patch = parts.indices.contains(2) ? parts[2] : 0
    }

    public var isSupported: Bool {
        self >= .minimumSupported && self < .firstUnsupported
    }

    public var description: String {
        "\(major).\(minor).\(patch)"
    }

    public static func < (lhs: PythonVersion, rhs: PythonVersion) -> Bool {
        if lhs.major != rhs.major { return lhs.major < rhs.major }
        if lhs.minor != rhs.minor { return lhs.minor < rhs.minor }
        return lhs.patch < rhs.patch
    }
}

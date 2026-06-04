cask "mdify" do
  version "0.2.0"
  arch arm: "AppleSilicon", intel: "Intel"

  sha256 arm:   "a1369bf91c24a2be880b0df7f53a8eae5cdee444c4643c4941c82cc7c24d5c6b",
         intel: "99dd0c5b3cf12617b37c0fbc11f3e1caa937f83a407e6a9406e1c71efccc6608"

  url "https://github.com/MikeBelousov/MDify/releases/download/v#{version}/MDify-Lite-#{arch}.zip"

  name "MDify Lite"
  desc "Native macOS document to Markdown converter with embedded MarkItDown worker"
  homepage "https://github.com/MikeBelousov/MDify"

  app "MDify Lite.app"

  caveats <<~EOS
    MDify Lite is unsigned and not notarized.
    If macOS blocks first launch, run:

      xattr -dr com.apple.quarantine "/Applications/MDify Lite.app"
      open -a "MDify Lite"
  EOS
end

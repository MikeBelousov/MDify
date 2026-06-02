cask "mdify" do
  version "0.1.0"
  sha256 "739eb49234894fdd5b983c9782f3374b36a2bbb1d2ea892b45e8844c41f68a98"

  url "https://github.com/MikeBelousov/MDify/releases/download/v#{version}/MDify.zip"
  name "MDify"
  desc "Native macOS document to Markdown converter powered by MarkItDown"
  homepage "https://github.com/MikeBelousov/MDify"

  app "MDify.app"

  caveats <<~EOS
    MDify v0 is unsigned and not notarized.
    If macOS blocks first launch, run:

      xattr -dr com.apple.quarantine /Applications/MDify.app
      open -a MDify
  EOS
end

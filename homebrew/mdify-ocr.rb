cask "mdify-ocr" do
  version "0.2.0"
  arch arm: "AppleSilicon", intel: "Intel"

  sha256 arm:   "314aa3e24209f8091e6233b5e3cf52cbd8b3963598e2181e6a39a3617afb4e4e",
         intel: "e44fba46086e3811ff17d1fa6ba0161b1bad353d490380ce13ae3f3c7fb3791f"

  url "https://github.com/MikeBelousov/MDify/releases/download/v#{version}/MDify-OCR-#{arch}.zip"

  name "MDify OCR"
  desc "Native macOS document to Markdown converter with embedded OCR worker"
  homepage "https://github.com/MikeBelousov/MDify"

  app "MDify OCR.app"

  caveats <<~EOS
    MDify OCR is unsigned and not notarized.
    If macOS blocks first launch, run:

      xattr -dr com.apple.quarantine "/Applications/MDify OCR.app"
      open -a "MDify OCR"
  EOS
end

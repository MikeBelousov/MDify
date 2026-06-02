# MDify

MDify is a native macOS app for converting local documents to Markdown using
Microsoft's MarkItDown Python package.

MDify is not a Microsoft product. It is an open source macOS wrapper around the
MarkItDown command-line tool.

## Install

Download `MDify.zip` from the latest GitHub release:

https://github.com/MikeBelousov/MDify/releases

Unzip it, move `MDify.app` to `/Applications`, and open it.

The v0 release is unsigned and not notarized. If macOS blocks first launch, run:

```bash
xattr -dr com.apple.quarantine /Applications/MDify.app
open -a MDify
```

## Requirements

- macOS 14+
- Python 3.10-3.13
- For development: Xcode 16.2 recommended

MDify does not install Python automatically. On first launch it looks for a
compatible Python, creates its own virtual environment in
`~/Library/Application Support/MDify/Python/venv`, and installs
`markitdown[all]==0.1.6` there.

Python 3.14 is intentionally ignored in v0 because at least one dependency in
`markitdown[all]==0.1.6` does not currently publish a compatible 3.14 release.

## Features

- Add individual local files.
- Add a whole folder from the toolbar, menu, or drag-and-drop.
- Skip unsupported, hidden, system, package, and symlink entries during folder import.
- Confirm whether folder import should include subfolders.
- Preserve folder structure when writing Markdown outputs.
- Preview, copy, and reveal generated Markdown.

Folder imports are written under the selected output folder. By default that is
Downloads. For example, importing `Research/Notes/source.txt` writes to
`~/Downloads/Research/Notes/source.md`.

## Build and Run

```bash
./script/build_and_run.sh
```

The script builds the SwiftPM app, stages `dist/MDify.app`, and launches it as a
normal macOS application bundle.

You can also open the project in Xcode by opening `Package.swift`. A separate
`.xcodeproj` is not required for development; SwiftPM is the project entrypoint.

If Xcode lives on the Desktop, the script uses:

```bash
DEVELOPER_DIR=~/Desktop/Xcode.app/Contents/Developer
```

## Build a Release Archive

```bash
./script/build_release.sh
```

The release archive is written to `dist/MDify.zip`.

## Future Homebrew Install

The intended first release install command is:

```bash
brew install --cask mikebelousov/tap/mdify
```

The cask template is in `homebrew/mdify.rb`. It should be copied to the
Homebrew tap after the GitHub release asset is published.

## License

MIT. See `LICENSE` and `ThirdPartyNotices.md`.

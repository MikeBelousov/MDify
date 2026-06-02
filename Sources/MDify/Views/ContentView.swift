import MDifyCore
import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @EnvironmentObject private var appState: AppState
    @EnvironmentObject private var conversionService: ConversionService
    @State private var isDropTargeted = false

    var body: some View {
        NavigationSplitView {
            SidebarQueueView()
                .navigationSplitViewColumnWidth(min: 260, ideal: 320, max: 420)
        } detail: {
            DetailView()
        }
        .toolbar {
            ToolbarItemGroup {
                Button {
                    appState.chooseFiles()
                } label: {
                    Label("Add Files", systemImage: "plus")
                }

                Button {
                    appState.chooseFolder()
                } label: {
                    Label("Add Folder", systemImage: "folder.badge.plus")
                }

                Button {
                    appState.chooseOutputDirectory()
                } label: {
                    Label("Output", systemImage: "folder")
                }

                Button {
                    Task { await appState.convertAll() }
                } label: {
                    Label("Convert All", systemImage: "arrow.triangle.2.circlepath")
                }
                .disabled(conversionService.items.isEmpty || conversionService.isConverting)

                Button {
                    conversionService.cancel()
                } label: {
                    Label("Cancel", systemImage: "stop")
                }
                .disabled(!conversionService.isConverting)

                Button {
                    appState.copySelectedMarkdown()
                } label: {
                    Label("Copy Markdown", systemImage: "doc.on.doc")
                }
                .disabled(conversionService.selectedItem?.markdownText.isEmpty ?? true)

                Button {
                    appState.revealSelectedOutput()
                } label: {
                    Label("Show in Finder", systemImage: "finder")
                }
                .disabled(!appState.canRevealOutput(for: conversionService.selectedItem))
            }
        }
        .overlay {
            if isDropTargeted {
                RoundedRectangle(cornerRadius: 8)
                    .stroke(.tint, lineWidth: 3)
                    .padding(10)
                    .allowsHitTesting(false)
            }
        }
        .onDrop(of: [UTType.fileURL.identifier], isTargeted: $isDropTargeted, perform: handleDrop)
        .task {
            await appState.bootstrapIfNeeded()
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                let url: URL?
                if let data = item as? Data {
                    url = URL(dataRepresentation: data, relativeTo: nil)
                } else {
                    url = item as? URL
                }

                if let url {
                    Task { @MainActor in
                        appState.importURLs([url])
                    }
                }
            }
        }
        return true
    }
}

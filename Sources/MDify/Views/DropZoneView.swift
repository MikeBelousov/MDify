import SwiftUI

struct DropZoneView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        VStack(spacing: 18) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 56))
                .foregroundStyle(.secondary)
            Text("Drop documents to convert")
                .font(.title2)
                .fontWeight(.semibold)
            HStack {
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
                    Label("Choose Output", systemImage: "folder")
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

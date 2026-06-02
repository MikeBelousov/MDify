import SwiftUI

@main
struct MDifyApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .environmentObject(appState.conversionService)
                .frame(minWidth: 980, minHeight: 640)
        }
        .commands {
            CommandMenu("Conversion") {
                Button("Add Files...") {
                    appState.chooseFiles()
                }
                .keyboardShortcut("o", modifiers: [.command])

                Button("Add Folder...") {
                    appState.chooseFolder()
                }
                .keyboardShortcut("o", modifiers: [.command, .option])

                Button("Choose Output Folder...") {
                    appState.chooseOutputDirectory()
                }
                .keyboardShortcut("o", modifiers: [.command, .shift])

                Button("Convert All") {
                    Task { await appState.convertAll() }
                }
                .keyboardShortcut(.return, modifiers: [.command])
            }
        }

        Settings {
            SettingsView()
                .environmentObject(appState)
                .frame(width: 560, height: 360)
        }
    }
}

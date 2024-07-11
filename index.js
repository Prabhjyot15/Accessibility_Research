import { app, BrowserWindow, globalShortcut } from "electron";
import path from "path";
import { fileURLToPath } from "url";

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    show: false, // Optional: Start with the window hidden
    webPreferences: {
      // Optional: Preload script
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // Load your tutoria11y.js script here
  mainWindow.loadFile(path.join(__dirname, "tutoria11y.js"));

  // Optionally open DevTools for debugging
  mainWindow.webContents.openDevTools();

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.on("ready", createWindow);

// Quit when all windows are closed, except on macOS
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

// Register global shortcuts here if needed
// Example:
// globalShortcut.register('CommandOrControl+Shift+I', () => {
//   console.log('Global shortcut activated');
// });

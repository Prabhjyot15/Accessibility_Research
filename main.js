const { app, shell, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const say = require('say');
const { GlobalKeyboardListener } = require('node-global-key-listener');
const processWindows = require('node-process-windows');
const { exec } = require('child_process');

let mainWindow;

// Function to open Slack
const openSlack = () => {
  const slackPath = 'C:\\Users\\Prabhjyot\\AppData\\Local\\slack\\slack.exe'; // Replace with actual path
  shell.openPath(slackPath);
};

// Function to create main Electron window
const createWindow = () => {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: true,
      contextIsolation: false,
      accessibilityValidation: false // Enable accessibility tree
    }
  });

  mainWindow.loadFile('index.html'); // Replace with your HTML file
  mainWindow.webContents.openDevTools(); // Optional: Open DevTools for debugging

  mainWindow.on('closed', function () {
    mainWindow = null;
  });

  // Listen for accessibility tree updates
  mainWindow.webContents.on('did-attach-accessibility-tree', (event, accessibleTree, rawAccessibilityTree) => {
    console.log('Accessibility tree updated:', accessibleTree);
    mainWindow.webContents.send('accessibility-tree-updated', accessibleTree); // Send to renderer process
  });
};

// Initialize Electron app
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit app when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Function to read out a step description using text-to-speech
const readStep = (step) => {
  return new Promise((resolve, reject) => {
    const voice = "Microsoft David Desktop"; // or 'Microsoft Zira Desktop'
    say.speak(step.description, voice, 1.0, (err) => {
      if (err) {
        console.error("Error speaking:", err);
        reject(err);
      } else {
        resolve();
      }
    });
  });
};

// Function to handle success
const handleSuccess = (listener, resolve) => {
  listener.stop();
  resolve(true);
};

// Function to handle failure
const handleFailure = (index) => {
  return 0; // Reset index
};

// Function to handle keypress events
const handleKeypress = (e, action, index, pressedKeys, listener, resolve) => {
  const pressedKey = e.name.toLowerCase();
  console.log(`Pressed key: ${pressedKey}`);

  // Normalize pressed key
  const normalizePressedKey = (key) => {
    switch (key) {
      case "left ctrl":
      case "right ctrl":
        return "ctrl";
      case "left shift":
      case "right shift":
        return "shift";
      case "forward slash":
        return "/";
      default:
        return key.toLowerCase();
    }
  };

  const normalizedPressedKey = normalizePressedKey(pressedKey);

  // Handle key down event
  if (e.state === "DOWN" && !pressedKeys[normalizedPressedKey]) {
    pressedKeys[normalizedPressedKey] = true;
    const expectedString = action.value ? action.value.toLowerCase() : "";
    const expectedKeys = action.keys ? action.keys.map((key) => key.toLowerCase()) : [];

    switch (action.type) {
      case "string":
        if (normalizedPressedKey === expectedString[index]) {
          index++;
          if (index === expectedString.length) {
            handleSuccess(listener, resolve);
          }
        } else {
          index = handleFailure(index);
        }
        break;
      case "keyboard":
        if (normalizedPressedKey === expectedKeys[index]) {
          index++;
          if (index === expectedKeys.length) {
            handleSuccess(listener, resolve);
          }
        } else {
          index = handleFailure(index);
        }
        break;
      case "tab":
        if (normalizedPressedKey === "tab") {
          index++;
          if (index === action.count) {
            handleSuccess(listener, resolve);
          }
        } else {
          index = handleFailure(index);
        }
        break;
    }
  }

  // Handle key up event
  if (e.state === "UP") {
    delete pressedKeys[normalizedPressedKey];
  }

  return { success: false, index };
};

// Function to simulate keyboard input based on action type in Slack
const simulateActionInSlack = async (action) => {
  return new Promise((resolve, reject) => {
    const listener = new GlobalKeyboardListener();
    let success = false;
    let index = 0;
    let pressedKeys = {};

    const handleKeypressWrapper = (e) => {
      const result = handleKeypress(e, action, index, pressedKeys, listener, resolve);
      index = result.index;
      if (result.success) {
        success = true;
      }
    };

    listener.addListener(handleKeypressWrapper);
    listener.start();
    switch (action.type) {
      case "string":
        console.log(`Enter string: ${action.value}`);
        break;
      case "keyboard":
        console.log(`Press: ${action.keys.join(" + ")} (no Enter needed):`);
        break;
      case "tab":
        console.log(`Press the Tab key ${action.count} times.`);
        break;
    }

    setTimeout(() => {
      if (!success) {
        listener.stop();
        reject(new Error("Action timeout"));
      }
    }, 60000);
  });
};

// Function to run the tutorial
const runTutorial = async (tutorialFile) => {
  try {
    const tutorialData = JSON.parse(fs.readFileSync(tutorialFile));
    const steps = tutorialData.steps;

    // Open Slack and run tutorial
    // openSlack();
    // await waitForSlackActive();

    for (let step of steps) {
      await readStep(step);
      await simulateActionInSlack(step.action);
      console.log("Step completed successfully.\n");
    }
    console.log("Tutorial completed.");
  } catch (error) {
    console.error("Error during tutorial:", error);
  }
};

// Function to wait until Slack is active
const waitForSlackActive = async () => {
  let slackActive = false;
  while (!slackActive) {
    try {
      const window = await processWindows.getActiveWindow();
      console.log("Active window:", window); // Log window details
      if (window && window.fileName && window.fileName.toLowerCase().includes("slack.exe")) {
        slackActive = true;
      } else {
        console.log("Slack is not active. Waiting...");
        await delay(1000); // Wait 1 second before checking again
      }
    } catch (err) {
      console.error("Error checking active window:", err);
      await delay(1000); // Wait 1 second before checking again on error
    }
  }
};

// Utility function to delay execution
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// IPC Event Handler to start tutorial from renderer process
ipcMain.on('start-tutorial', (event, tutorialFile) => {
  runTutorial(tutorialFile);
});

// IPC Event Handler to get the UI tree from .NET application
ipcMain.on('get-ui-tree', (event) => {
  exec('dotnet run UIAutomationDemo.csproj', (error, stdout, stderr) => {
    if (error) {
      console.error(`Error running .NET application: ${error.message}`);
      return;
    }
    if (stderr) {
      console.error(`stderr: ${stderr}`);
      return;
    }

    // Send the UI tree data to the renderer process
    mainWindow.webContents.send('ui-tree-updated', stdout);
  });
});

// IPC Event Handler to send accessibility tree updates to renderer process
ipcMain.on('get-accessibility-tree', (event) => {
  mainWindow.webContents.send('get-accessibility-tree');
});

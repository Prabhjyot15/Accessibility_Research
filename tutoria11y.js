import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import say from "say";
import { GlobalKeyboardListener } from "node-global-key-listener";

// Get the directory name of the current module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load steps from JSON file
const steps = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "./accessibility-guides/create-channel-private.json")
  )
).steps;

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
const handleKeypress = (
  e,
  down,
  action,
  index,
  pressedKeys,
  listener,
  resolve
) => {
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
  if (e.state == "DOWN" && !pressedKeys[normalizedPressedKey]) {
    pressedKeys[normalizedPressedKey] = true;
    const expectedString = action.value ? action.value.toLowerCase() : "";
    const expectedKeys = action.keys
      ? action.keys.map((key) => key.toLowerCase())
      : [];

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
  if (e.state == "UP") {
    delete pressedKeys[normalizedPressedKey];
  }

  return { success: false, index };
};

// Function to simulate keyboard input based on action type
const simulateAction = async (action) => {
  return new Promise((resolve, reject) => {
    const listener = new GlobalKeyboardListener();
    let success = false;
    let index = 0;
    let pressedKeys = {};

    const handleKeypressWrapper = (e, down) => {
      const result = handleKeypress(
        e,
        down,
        action,
        index,
        pressedKeys,
        listener,
        resolve
      );
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

// Main function to run the tutorial
const runTutorial = async () => {
  try {
    for (let step of steps) {
      await readStep(step);
      await simulateAction(step.action);
      console.log("Step completed successfully.\n");
    }
    console.log("Tutorial completed.");
  } catch (error) {
    console.error("Error during tutorial:", error);
  }
};

runTutorial();

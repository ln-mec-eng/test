const fs = require('fs');
const path = require('path');

const directoryPath = path.join(__dirname, 'sass');
const bridgeTokensPath = path.join(__dirname, 'sass', 'libs', '_bridge-tokens.scss');

// 1. Gather all unique variables
const regex = /var\(--_?[🎨🔠🔘📏]-?([^\)]+)\)/g;
const uniqueVars = new Set();
const varMap = new Map(); // original -> new name

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walkDir(dirPath, callback) : callback(path.join(dir, f));
  });
}

// Pass 1: Find all variables
walkDir(directoryPath, function(filePath) {
  if (filePath.endsWith('.scss')) {
    const content = fs.readFileSync(filePath, 'utf8');
    let match;
    while ((match = regex.exec(content)) !== null) {
        uniqueVars.add(match[0]); // var(--_🎨-color--tokens---button-secondary-default--text)
    }
  }
});


// 2. Generate new names
uniqueVars.forEach(originalVarCall => {
    // Extract the inner variable name
    // e.g. --_🎨-color--tokens---button-secondary-default--text
    const innerVarMatch = originalVarCall.match(/var\((--_?[🎨🔠🔘📏]-?([^\)]+))\)/);
    if (innerVarMatch) {
       const fullInnerVar = innerVarMatch[1]; // --_🎨-color--tokens---button-secondary...
       let cleanName = innerVarMatch[2]; // color--tokens---button-secondary...
       
       // Clean up the name to make it a nice SCSS variable
       cleanName = cleanName.replace(/---+/g, '-');
       cleanName = cleanName.replace(/--+/g, '-');
       
       // Remove redundant prefixes if they exist (e.g., color-tokens, typography)
       cleanName = cleanName.replace(/^color-tokens-/, 'color-');
       cleanName = cleanName.replace(/^typography-/, '');
       
       // Remove any trailing dashes
       cleanName = cleanName.replace(/-$/, '');
       
       // Create the SCSS variable name
       const scssVarName = `$${cleanName}`;
       
       varMap.set(originalVarCall, {
           fullInnerVar: fullInnerVar,
           scssVarName: scssVarName
       });
    }
});

// 3. Generate _bridge-tokens.scss content
let bridgeContent = `// --------------------------------------------------------
// Bridge Tokens (Customizable)
// --------------------------------------------------------
// To override the library tokens, you can redefine these CSS variables
// in a :root block below or in your main stylesheet.
//
// :root {
//   --_🔘-radius---small: 4px;
//   --_🎨-color--base---neutral--dark-0: #ffffff;
// }

`;

// Sort variables for better readability in the generated file
const sortedVars = Array.from(varMap.values()).sort((a, b) => a.scssVarName.localeCompare(b.scssVarName));

sortedVars.forEach(v => {
   bridgeContent += `${v.scssVarName}: var(${v.fullInnerVar});\n`;
});

// Write _bridge-tokens.scss
fs.writeFileSync(bridgeTokensPath, bridgeContent, 'utf8');
console.log(`Generated ${bridgeTokensPath} with ${sortedVars.length} variables.`);

// 4. Replace in all SCSS files
let filesModified = 0;
walkDir(directoryPath, function(filePath) {
  if (filePath.endsWith('.scss')) {
      let content = fs.readFileSync(filePath, 'utf8');
      let originalContent = content;
      
      varMap.forEach((value, key) => {
         // Escape the key for regex replacement globally
         // e.g. var(--_🎨-color...) -> \$color...
         const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
         const replaceRegex = new RegExp(escapedKey, 'g');
         content = content.replace(replaceRegex, value.scssVarName);
      });
      
      if (content !== originalContent) {
          fs.writeFileSync(filePath, content, 'utf8');
          filesModified++;
          console.log(`Updated ${filePath}`);
      }
  }
});

console.log(`\nFinished! Modified ${filesModified} files.`);

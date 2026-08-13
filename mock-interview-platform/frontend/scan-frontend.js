#!/usr/bin/env node
/**
 * Frontend problem scanner for Next.js and React components
 */

const fs = require('fs');
const path = require('path');

console.log('='.repeat(70));
console.log('FRONTEND PROBLEM SCAN');
console.log('='.repeat(70));

const checkPath = 'c:\\Users\\dell\\OneDrive\\Desktop\\AI Mock Interview Platform\\mock-interview-platform\\frontend';

// Test 1: Check critical files exist
console.log('\n[1] Checking critical files...');
const criticalFiles = [
  'package.json',
  'next.config.js',
  'src/app/layout.js',
  'src/app/page.js',
  'src/utils/api.js',
  'src/components/Navigation.js',
  'src/app/subscription/page.js',
  'src/components/SubscriptionUsageAlert.js',
  'src/components/FeatureGate.js',
];

let missingFiles = [];
for (const file of criticalFiles) {
  const fullPath = path.join(checkPath, file);
  if (!fs.existsSync(fullPath)) {
    missingFiles.push(file);
  }
}

if (missingFiles.length > 0) {
  console.log(`  ❌ Missing files: ${missingFiles.join(', ')}`);
} else {
  console.log(`  ✅ All ${criticalFiles.length} critical files present`);
}

// Test 2: Check API client functions
console.log('\n[2] Checking API client functions...');
const apiPath = path.join(checkPath, 'src/utils/api.js');
if (fs.existsSync(apiPath)) {
  const apiContent = fs.readFileSync(apiPath, 'utf8');
  const requiredFunctions = [
    'getSubscriptionStatus',
    'getUsageStats',
    'getBillingHistory',
    'upgradeSubscription',
    'startTrial',
    'getAvailableFeatures',
    'hasFeatureAccess',
  ];
  
  let missingFunctions = [];
  for (const func of requiredFunctions) {
    if (!apiContent.includes(`export const ${func}`) && !apiContent.includes(`const ${func}`)) {
      missingFunctions.push(func);
    }
  }
  
  if (missingFunctions.length > 0) {
    console.log(`  ⚠️  Missing API functions: ${missingFunctions.join(', ')}`);
  } else {
    console.log(`  ✅ All ${requiredFunctions.length} API functions present`);
  }
} else {
  console.log(`  ❌ api.js not found`);
}

// Test 3: Check subscription page
console.log('\n[3] Checking subscription page...');
const subPage = path.join(checkPath, 'src/app/subscription/page.js');
if (fs.existsSync(subPage)) {
  const content = fs.readFileSync(subPage, 'utf8');
  const checks = {
    'getSubscriptionStatus': 'subscription status function call',
    'getUsageStats': 'usage stats function call',
    'getBillingHistory': 'billing history function call',
    'createRazorpayOrder': 'Razorpay order creation',
  };
  
  let missing = [];
  for (const [func, desc] of Object.entries(checks)) {
    if (!content.includes(func)) {
      missing.push(desc);
    }
  }
  
  if (missing.length > 0) {
    console.log(`  ⚠️  Missing: ${missing.join(', ')}`);
  } else {
    console.log(`  ✅ Subscription page has all required functionality`);
  }
} else {
  console.log(`  ❌ subscription/page.js not found`);
}

// Test 4: Check component imports
console.log('\n[4] Checking component imports...');
const layoutPath = path.join(checkPath, 'src/app/layout.js');
if (fs.existsSync(layoutPath)) {
  const content = fs.readFileSync(layoutPath, 'utf8');
  
  const issues = [];
  if (content.includes('next/font/google')) {
    issues.push('Importing Google Fonts (can cause build hangs)');
  }
  if (!content.includes('Suspense')) {
    // This is ok, Suspense might not be in layout
  }
  
  if (issues.length > 0) {
    console.log(`  ⚠️  Issues found: ${issues.join(', ')}`);
  } else {
    console.log(`  ✅ Layout imports look good`);
  }
} else {
  console.log(`  ❌ layout.js not found`);
}

// Test 5: Check interview session page
console.log('\n[5] Checking interview session page...');
const sessionPage = path.join(checkPath, 'src/app/interview/session/page.js');
if (fs.existsSync(sessionPage)) {
  const content = fs.readFileSync(sessionPage, 'utf8');
  
  const checks = {
    'Suspense': 'Suspense wrapper for useSearchParams',
    'VideoRecorder': 'VideoRecorder component',
    'QuestionDisplay': 'QuestionDisplay component',
  };
  
  let missing = [];
  for (const [item, desc] of Object.entries(checks)) {
    if (!content.includes(item)) {
      missing.push(desc);
    }
  }
  
  if (missing.length > 0) {
    console.log(`  ⚠️  Missing: ${missing.join(', ')}`);
  } else {
    console.log(`  ✅ Interview session page is properly configured`);
  }
} else {
  console.log(`  ❌ interview/session/page.js not found`);
}

// Test 6: Check package.json dependencies
console.log('\n[6] Checking dependencies...');
const packagePath = path.join(checkPath, 'package.json');
if (fs.existsSync(packagePath)) {
  try {
    const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    const requiredDeps = [
      'react',
      'react-dom',
      'next',
      'axios',
    ];
    
    let missingDeps = [];
    const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };
    for (const dep of requiredDeps) {
      if (!allDeps[dep]) {
        missingDeps.push(dep);
      }
    }
    
    if (missingDeps.length > 0) {
      console.log(`  ❌ Missing dependencies: ${missingDeps.join(', ')}`);
    } else {
      console.log(`  ✅ All required dependencies present`);
    }
  } catch (e) {
    console.log(`  ❌ Could not parse package.json: ${e.message}`);
  }
} else {
  console.log(`  ❌ package.json not found`);
}

console.log('\n' + '='.repeat(70));
console.log('✅ FRONTEND SCAN COMPLETE');
console.log('='.repeat(70));

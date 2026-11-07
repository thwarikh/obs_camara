@echo off
echo Building OBS Camera Pro packages...

:: Android build
echo [Android] To build APK:
echo cd apps\android ^&^& gradlew.bat assembleRelease

:: iOS build
echo [iOS] To build Xcode package:
echo cd apps\ios ^&^& swift build


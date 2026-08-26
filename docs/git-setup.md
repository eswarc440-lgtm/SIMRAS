# Git and GitHub setup

The delivered folder is already a Git repository on the `main` branch.

## Push with GitHub CLI

```powershell
Set-Location simras-digital-twin
git status
gh auth login
gh repo create simras-digital-twin --public --source=. --remote=origin --push
```

## Push to a repository created in the browser

Create an empty repository without a generated README, then run:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/simras-digital-twin.git
git push -u origin main
```

## Working branch flow

```powershell
git switch -c phase-2-verified-assets
# Make and test changes
git add .
git commit -m "feat(data): add verified AP pilot assets"
git push -u origin phase-2-verified-assets
```

Never commit `.env`, raw restricted records, AWS credentials, large imagery or
unlicensed 3D files. GitHub Actions starts automatically after the push.


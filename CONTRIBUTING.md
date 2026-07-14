# Contribution Guidelines

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the linter: `shellcheck ani-cli providers/*.sh`
5. Test your changes manually (see PR template for test cases)
6. Open a pull request

## Pull Requests

- Follow conventional commit format: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- Bump the version in `ani-cli` (`version_number`)
- Update the README if your changes affect user-facing behavior
- Update the man page (`ani-cli.1`) if you add/modify CLI flags
- No extra dependencies unless absolutely necessary
- If fixing an issue, link it in the PR description

## Adding a Provider

1. Create `providers/yourprovider.sh`
2. Register with: `provider_register <id> <name> <extract_regex> [fetch_type]`
3. See `hacking.md` for detailed instructions on extraction regexes
4. Test that your provider returns links in debug mode

## Code Style

- Shell scripts: POSIX `sh` (not bash), 4-space indentation
- Python: PEP 8, 4-space indentation
- JavaScript: Standard JS style, 2-space indentation
- Avoid adding new dependencies

## Testing

Manual testing is required for all PRs. Use the test checklist in the PR template. Key test cases:
- Basic playback (sub + dub)
- Continue from history (`-c`)
- Download (`-d`)
- Range selection (`-e 1-10`)
- Provider switching
- Unicode titles and non-whole episodes (e.g., ep 24.5)

## Issues

- Use the issue templates
- When requesting a feature, check it hasn't been rejected before
- Provide reproduction steps for bugs
- Include debug logs if applicable

## How else can I help?

- Join the community discussions
- Take part in troubleshooting and testing
- Improve documentation
- Review open pull requests

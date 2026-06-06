# Contributing

Thanks for your interest! All contributions - bug reports, features, docs, translations - are welcome.

## Quick start

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-thing`
3. Make changes + add tests
4. Run lint + tests locally
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/)
6. Open a PR

## Commit format

```
feat: add VN30 sector mapping
fix: handle null volume in HOSE OHLC
docs: clarify rate-limit retry policy
test: add 429 retry coverage
```

## Code style

- **Python**: ruff + black (configured in `pyproject.toml`)
- **TypeScript**: eslint + prettier
- **R**: lintr + styler

## Reporting issues

Include:
- What you expected
- What happened instead
- Minimal reproduction (code + data sample)
- Environment (OS, Python/Node/R version, package version)

## License

By contributing, you agree your contributions are licensed under the repo's license (MIT unless stated otherwise).

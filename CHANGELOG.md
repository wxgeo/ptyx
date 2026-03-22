# CHANGELOG

<!-- version list -->

## v30.1.0 (2026-03-22)

### Bug Fixes

- Encoding issue with pdflatex logs.
  ([`5c65ca5`](https://github.com/wxgeo/ptyx/commit/5c65ca5c1e597efb5f94d5cdd0ee5c0c4ba74f17))

### Features

- Change the emplacement of the generated .plain-ptyx file.
  ([`f751d13`](https://github.com/wxgeo/ptyx/commit/f751d130f25ac67f9559151b334dd2c64b80a8fd))

### Testing

- Add assertion.
  ([`a289f44`](https://github.com/wxgeo/ptyx/commit/a289f44a89e9074f1afc257224a1b332d8231000))


## v30.0.0 (2025-10-30)

### Bug Fixes

- Keep comments' lines (as empty lines), to avoid shifting line numbers in tracebacks.
  ([`eb5a338`](https://github.com/wxgeo/ptyx/commit/eb5a33885a6af8d71b66fb477cf15a9e8158b9f0))

### Features

- Add #ALERT tag.
  ([`586fda3`](https://github.com/wxgeo/ptyx/commit/586fda34766fbb19498d493a474c2dddd150f948))

- Improve feedback API.
  ([`b471d00`](https://github.com/wxgeo/ptyx/commit/b471d003f10e3b090646153a723413acaf12c598))

- New bold() method for pretty printing.
  ([`8bf632b`](https://github.com/wxgeo/ptyx/commit/8bf632b798ffdf188784aff9194b6349c97d71d4))


## v29.2.0 (2025-02-20)

### Bug Fixes

- Fix feedback function API.
  ([`b7ee729`](https://github.com/wxgeo/ptyx/commit/b7ee7298878de8fae8c4425980507d5066d1577a))

### Features

- Create a trackback for ptyx files inclusions.
  ([`0255d83`](https://github.com/wxgeo/ptyx/commit/0255d83fd8ed2bff328b6c8c0f2fce2fde20e0e4))

- Do not resolve symlinks when setting working directory.
  ([`d17a617`](https://github.com/wxgeo/ptyx/commit/d17a617c168e7e1d3370eec005b42308909ebdde))

- New compilation algorithm, adding the ability to call a function at each compilation.
  ([`6901c30`](https://github.com/wxgeo/ptyx/commit/6901c30effd99b86a8e95715ba0ab8c4704dfd84))


## v29.1.0 (2024-11-08)

### Features

- Add the `parse_extended_python_line()` function.
  ([`577b708`](https://github.com/wxgeo/ptyx/commit/577b708c2ba1a5908cb25446cdacdc8d7d7c0f79))


## v29.0.0 (2024-11-06)

### Bug Fixes

- Fix bug in expression parser (incorrect string characters escape).
  ([`d4e385d`](https://github.com/wxgeo/ptyx/commit/d4e385d56b7c462dfe44224d5dd6920cc9771b74))

- Fix small issue in error formatting.
  ([`2d0b3b2`](https://github.com/wxgeo/ptyx/commit/2d0b3b2f9cf9097ff3d9413c955c3a152a8b1180))

### Features

- Add `CompilationOptions.updated()` method.
  ([`12c97fc`](https://github.com/wxgeo/ptyx/commit/12c97fcc3394b6dd022f728ce6e60b4f47b6cdbf))

- Add `force_hardlink_to()` to `utilities.py`.
  ([`ca1baae`](https://github.com/wxgeo/ptyx/commit/ca1baaee85e7867f9022e1cbff754ebcd93f00b9))

- Create hardlinks instead of copying compiled files.
  ([`0a86fbb`](https://github.com/wxgeo/ptyx/commit/0a86fbb6027ba221627d9af93098c09411fc3552))

- Improve errors data, to enable better interactions with IDE.
  ([`078d1d7`](https://github.com/wxgeo/ptyx/commit/078d1d72b147c122d4cfcb707febc0ceb73dfd7a))

- Make_files return compiler instance too.
  ([`b8f87eb`](https://github.com/wxgeo/ptyx/commit/b8f87ebc90437354e3eb12acee7c10bab5a84da3))

- PythonCodeBlockError is now fully pickable.
  ([`b997f9a`](https://github.com/wxgeo/ptyx/commit/b997f9a64b79ef6dd7a48a32985e840fd5b3f07a))

- Support italic in shell.
  ([`a01f4f8`](https://github.com/wxgeo/ptyx/commit/a01f4f818912d59b3c50829fd7b24489112523a0))

### Testing

- Add test for --compress option.
  ([`867b86a`](https://github.com/wxgeo/ptyx/commit/867b86a1f0cc3e2ee1bf222aae0931326c2ed14f))


## v28.2.0 (2024-02-09)

### Features

- Improve error messages and create custom exceptions.
  ([`b51f9e3`](https://github.com/wxgeo/ptyx/commit/b51f9e3093f7a14cb61c770006e5006393d4ae08))

- Support passing some sympy flags to latex printers, notably `mat_str`.
  ([`657132b`](https://github.com/wxgeo/ptyx/commit/657132bb554f71007693b9b5ffde1b2dec0722f5))


## v28.1.1 (2024-01-26)

### Bug Fixes

- Support extended python delimiter even if there is no linebreak before.
  ([`c62c32a`](https://github.com/wxgeo/ptyx/commit/c62c32a35d47b97e4af9e1481590309427ddf003))


## v28.1.0 (2024-01-26)

### Features

- VERBATIM tag content is now preserved when parsing extended python syntax.
  ([`564fbba`](https://github.com/wxgeo/ptyx/commit/564fbba47f3806255e2162a29e07dae929b2c84f))


## v28.0.0 (2024-01-20)

### Bug Fixes

- Change parsing of tags to accept underscores in variable names.
  ([`ee05057`](https://github.com/wxgeo/ptyx/commit/ee050570037c35c00885d264f8d7316081c1025c))

- Don't exceed document number target.
  ([`07a837e`](https://github.com/wxgeo/ptyx/commit/07a837ed6a6184cc49a5c6c9c68dbe02d9c7c4d5))

- Fix previous commit.
  ([`b92c1a2`](https://github.com/wxgeo/ptyx/commit/b92c1a2378d0d3a983f494327c2fa6efe07e4546))

### Features

- Add a sandboxed `randsample()` function.
  ([`16a952b`](https://github.com/wxgeo/ptyx/commit/16a952ba0ebdb68e73f486cdc783667f4eaa9ecb))

- Add new flag `?` to EVAL tag, used to hide implicit `1` when multiplying.
  ([`f1025c9`](https://github.com/wxgeo/ptyx/commit/f1025c9e8a6e3e5924c2f8cd11b7b52c10e1939d))

- Add option --view to display generated pdf with default viewer.
  ([`4b9ae4f`](https://github.com/wxgeo/ptyx/commit/4b9ae4f265a0c76831cb5cc82377e56786071c33))

- Change #* tag behaviour, taking into account previous evaluation.
  ([`d868553`](https://github.com/wxgeo/ptyx/commit/d86855358292de98b340c140830b99c4e7442879))

- Implement new option `same-number-of-pages-compact`.
  ([`3273ab1`](https://github.com/wxgeo/ptyx/commit/3273ab150cbf5a4b328f12f935da5653a896ff2e))

- Improve `*` flag behaviour when evaluation an expression.
  ([`9a88062`](https://github.com/wxgeo/ptyx/commit/9a88062cb3dcbe13ab70c3acc0a18cb963367f2a))

- Nicer `~` character in verbatim mode.
  ([`4b4e9f7`](https://github.com/wxgeo/ptyx/commit/4b4e9f7aa17c641111fc4261c7980c901f6ba76b))

- Nicer error message when an unknown flag is seen.
  ([`4fcdbe9`](https://github.com/wxgeo/ptyx/commit/4fcdbe9d612b0875667b103d68f257a310f22aad))

- Python delimiter of extension `extended_python` can now be accessed via `PYTHON_DELIMITER`
  variable.
  ([`02350bb`](https://github.com/wxgeo/ptyx/commit/02350bb9f9316db49294ffaf160402447fe329e3))

### Testing

- Add a test for last commit (and fix some remaining bugs).
  ([`f28972f`](https://github.com/wxgeo/ptyx/commit/f28972f1240932bf78eae9a0679b02d561457ff6))


## v27.0.0 (2023-11-21)

### Features

- Rename CLI options and fully refactor options handling code.
  ([`f03ad99`](https://github.com/wxgeo/ptyx/commit/f03ad99da1904b53c5739907a3ea1ff013e92dae))

### Refactoring

- Change make_files() signature.
  ([`8762323`](https://github.com/wxgeo/ptyx/commit/87623237a7c2f249e0e81c4a081b3bcc2667a689))

- Create file `sys_info.py` to gather platform information.
  ([`4719e68`](https://github.com/wxgeo/ptyx/commit/4719e6810a6fb9947a33ce24f2ce25e39078cb7c))

- Remove `make_file()` and create a new `compile_ptyx_file()` function instead.
  ([`4b59fbb`](https://github.com/wxgeo/ptyx/commit/4b59fbb4abe7a8857e407d1876ac3f954243fedd))

- Remove global compiler instance (at last!)
  ([`124db58`](https://github.com/wxgeo/ptyx/commit/124db58933be96e2b7ac25080e213706c85b19e1))

### Testing

- Add tests for #ASK, #ASK_ONLY, #ANS and #ANSWER tags.
  ([`2d4be53`](https://github.com/wxgeo/ptyx/commit/2d4be536ea12efd40d7f37c2e7cfb15bd8a9522e))


## v26.0.1 (2023-11-20)

### Bug Fixes

- Fix regression when concatening pdf files.
  ([`74cd4e7`](https://github.com/wxgeo/ptyx/commit/74cd4e7951f73e5520c1bb20cf1acce8a7e8a189))


## v26.0.0 (2023-11-20)

### Bug Fixes

- Support non-utf8 output for commands.
  ([`9e705ab`](https://github.com/wxgeo/ptyx/commit/9e705ab0603d072b9fea26e6ab63e75fc6fac86b))

### Features

- Change `compile_latex()` and `make_file()` signature, to return compilation errors too.
  ([`3977152`](https://github.com/wxgeo/ptyx/commit/3977152c3d6a176b9bb5ff6723293c649a35c791))

- Change `make_files()` signature to return much more compilation information.
  ([`46eaf27`](https://github.com/wxgeo/ptyx/commit/46eaf27ea4ce1d778933fa6d6a68d03aea753955))

- Make LaTeX errors much more explicit.
  ([`6126d3c`](https://github.com/wxgeo/ptyx/commit/6126d3cbc6fa624d900f6e02aeb53bd77fdb3f81))

### Testing

- Remove flake8, use ruff instead.
  ([`aa5108e`](https://github.com/wxgeo/ptyx/commit/aa5108e1951088af20a3d65afe20ad5435031e21))


## v25.0.1 (2023-10-17)

### Bug Fixes

- Fix major regression in optional arguments parsing.
  ([`525b07d`](https://github.com/wxgeo/ptyx/commit/525b07d7c8aae3f094178a4a5dfda4e3e3fcfac6))


## v25.0.0 (2023-10-17)

### Bug Fixes

- Fix small issues with hash symbols inside a tag argument.
  ([`bca464c`](https://github.com/wxgeo/ptyx/commit/bca464cc6312deaa4eadd8a8adf9aad65cb640e6))

- Handle the `\` character in python strings in `find_closing_brackets()`.
  ([`d788fde`](https://github.com/wxgeo/ptyx/commit/d788fdeae15ee1f79d117e36f3b29ddca2f97eb7))

### Features

- Change #PRINT{} tag, to interpret inner code. Fix a bug in compiler too.
  ([`26afb0f`](https://github.com/wxgeo/ptyx/commit/26afb0f6b0203594478764261e431cb0f18cc107))

### Refactoring

- ## is now handled directly par syntax parser, and not seens as a tag anymore.
  ([`0008de4`](https://github.com/wxgeo/ptyx/commit/0008de4b0b11956600c00cd0bb97734c9ae5f18d))

- Create a new updated LatexGenerator instance after loading extensions.
  ([`016d561`](https://github.com/wxgeo/ptyx/commit/016d56156297d40b745116c3281a7ef1963fdf31))

### Testing

- Update the tests concerning the PRINT tag.
  ([`cac0787`](https://github.com/wxgeo/ptyx/commit/cac0787a89f9240c37eb33d829dd12aa7b2698bc))


## v24.0.2 (2023-09-19)

### Bug Fixes

- Don't rely on hash() for generating seed, since it changes on each run by default.
  ([`27d41d1`](https://github.com/wxgeo/ptyx/commit/27d41d162f13cfe9af84fb412888e2123fe9366e))

- Remove old warning.
  ([`75d61d0`](https://github.com/wxgeo/ptyx/commit/75d61d0bd9c1b3a13e820ecba155e3a2903cd851))

### Build System

- Improve Makefile again.
  ([`aa4ab31`](https://github.com/wxgeo/ptyx/commit/aa4ab31e111952a3c2d863c5ab0e9b50cbc6780e))

- Remove old unused script entries in pyproject.toml.
  ([`5a9261b`](https://github.com/wxgeo/ptyx/commit/5a9261b8b08ad134eb9a0b7feafa4a023cade8c6))

- Update Makefile.
  ([`abf24c6`](https://github.com/wxgeo/ptyx/commit/abf24c697a28f0356d5eeb9b253afdc0f67c5059))

### Refactoring

- Keep #LOAD tags in plain ptyx file.
  ([`bc558d0`](https://github.com/wxgeo/ptyx/commit/bc558d0bc267339b73a98bc72d8c9a29c169a6e7))


## v24.0.1 (2023-06-27)

### Bug Fixes

- Update poetry.lock file and fix version number.
  ([`dcbc79d`](https://github.com/wxgeo/ptyx/commit/dcbc79dcb1d29f26081cf88f36ce3c0d152147f6))


## v24.0.0 (2023-06-27)

### Build System

- Add semantic_release to generate versions.
  ([`a088459`](https://github.com/wxgeo/ptyx/commit/a0884596b58c893600d5ebb9e7b6151fa3f1b25a))

- Update `poetry.lock`.
  ([`9ee98d4`](https://github.com/wxgeo/ptyx/commit/9ee98d46d5bb98d4b46d9b3370ea03b0565e6363))

### Features

- New plugin format.
  ([`c7e59e6`](https://github.com/wxgeo/ptyx/commit/c7e59e64296cfc88b7c3ef4259cee926e61f707d))

- Remove `__api__` variable and `API_VERSION` tag. Add `PTYX_VERSION` tag.
  ([`3823d5f`](https://github.com/wxgeo/ptyx/commit/3823d5f8e8a1fb3319766c2f630fa72c8589597c))

- Support for sympy 1.12.
  ([`7cf9cfc`](https://github.com/wxgeo/ptyx/commit/7cf9cfc5a81bea8613bbadbc2fed903999649f5c))

### Performance Improvements

- Just calling `ptyx --help` is much faster now.
  ([`65fe63c`](https://github.com/wxgeo/ptyx/commit/65fe63ca280eff5e88d06af2b0ea0a80760e10b1))


## v22.4.1 (2023-01-22)


## v22.3.2 (2023-01-01)


## v22.3.1 (2022-07-01)


## v19.8.1 (2019-08-20)

- Initial Release

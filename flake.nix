{
  description = "Run commands against code blocks in documentation files";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;

        # Version for setuptools-scm: use git short rev for dev builds
        version = "0.0.0+${self.shortRev or self.dirtyShortRev or "unknown"}";

        # Override setuptools-scm to a newer version required by click-compose
        setuptools-scm-new = python.pkgs.setuptools-scm.overridePythonAttrs (old: rec {
          version = "9.2.2";
          src = python.pkgs.fetchPypi {
            pname = "setuptools_scm";
            inherit version;
            hash = "sha256-HGdKtGZWhqCIfX4kwDqyXyQgHCE+guponS8+Fp7371c=";
          };
        });

        # Override beartype to a newer version required by sybil-extras
        beartype-new = python.pkgs.beartype.overridePythonAttrs (old: rec {
          version = "0.22.9";
          src = python.pkgs.fetchPypi {
            pname = "beartype";
            inherit version;
            hash = "sha256-j4K1SqcjooSKVgCNGIdfkcHbAsMu9qYjGaAC4+Jal18=";
          };
        });

        # Override sybil to a newer version required by sybil-extras
        sybil-new = python.pkgs.sybil.overridePythonAttrs (old: rec {
          version = "9.3.0";
          src = python.pkgs.fetchPypi {
            pname = "sybil";
            inherit version;
            hash = "sha256-hH0dF7ioV8S7P4RxtKV7iv+pOaYPv1B+cKpyrXkJfAU=";
          };
        });

        click-compose = python.pkgs.buildPythonPackage rec {
          pname = "click-compose";
          version = "2025.10.27.3";
          pyproject = true;

          src = python.pkgs.fetchPypi {
            pname = "click_compose";
            inherit version;
            hash = "sha256-bTMmoTtpCseg8Omd54WqeOqB0TC6AtYJ5jZ6evI0d6U=";
          };

          build-system = [
            python.pkgs.setuptools
            setuptools-scm-new
          ];

          dependencies = [
            beartype-new
            python.pkgs.click
          ];

          pythonImportsCheck = [ "click_compose" ];
        };

        sybil-extras = python.pkgs.buildPythonPackage rec {
          pname = "sybil-extras";
          version = "2025.12.13.4";
          pyproject = true;

          src = python.pkgs.fetchPypi {
            pname = "sybil_extras";
            inherit version;
            hash = "sha256-OMrM4XJEE/O3AfhAAQppUIjWfoYC6tZlMOMW4Q7ytlE=";
          };

          build-system = [
            python.pkgs.setuptools
            setuptools-scm-new
          ];

          dependencies = [
            beartype-new
            sybil-new
          ];

          pythonImportsCheck = [ "sybil_extras" ];
        };

        doccmd = python.pkgs.buildPythonApplication {
          pname = "doccmd";
          inherit version;
          pyproject = true;

          src = ./.;

          build-system = with python.pkgs; [
            setuptools
            setuptools-scm
          ];

          dependencies = with python.pkgs; [
            charset-normalizer
            click
            cloup
            pygments
          ] ++ [
            beartype-new
            click-compose
            sybil-extras
            sybil-new
          ];

          # Skip tests as they require many additional dependencies
          doCheck = false;

          # setuptools-scm needs git - use git rev for dev builds
          SETUPTOOLS_SCM_PRETEND_VERSION = version;

          pythonImportsCheck = [ "doccmd" ];

          meta = with pkgs.lib; {
            description = "Run commands against code blocks in documentation files";
            homepage = "https://github.com/adamtheturtle/doccmd";
            license = licenses.mit;
            maintainers = [ ];
            mainProgram = "doccmd";
          };
        };
      in
      {
        packages = {
          default = doccmd;
          doccmd = doccmd;
        };

        apps.default = flake-utils.lib.mkApp {
          drv = doccmd;
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ doccmd ];
          packages = [
            python
          ];
        };
      }
    );
}

## <a name="main_help"></a> python3 -m treepagegenerator.main --help
```
usage: python3 -m treepagegenerator.main [-h] [-la] [--listtools]
                                         {generate,info} ...

generate static pages containing tree search based on defined model

options:
  -h, --help       show this help message and exit
  -la, --logall    Log all messages (default: False)
  --listtools      List tools (default: False)

subcommands:
  use one of tools

  {generate,info}  one of tools
    generate       generate tree static pages
    info           print model info
```



## <a name="generate_help"></a> python3 -m treepagegenerator.main generate --help
```
usage: python3 -m treepagegenerator.main generate [-h] [-c CONFIG]
                                                  [-t TRANSLATION]
                                                  [--embedcss] [--embedimages]
                                                  [--singlepagemode]
                                                  [--outindexname OUTINDEXNAME]
                                                  --outdir OUTDIR

generate tree static pages

options:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to config file (default: None)
  -t TRANSLATION, --translation TRANSLATION
                        Path to translation file (default: None)
  --embedcss            Embed CSS styles (default: False)
  --embedimages         Embed images (default: False)
  --singlepagemode      Embed everything into single page (default: False)
  --outindexname OUTINDEXNAME
                        Name of main index page (default: index.html)
  --outdir OUTDIR       Path to output directory (default: None)
```



## <a name="info_help"></a> python3 -m treepagegenerator.main info --help
```
usage: python3 -m treepagegenerator.main info [-h] [-d DATA]

print model info

options:
  -h, --help            show this help message and exit
  -d DATA, --data DATA  Path to data file with model (default: None)
```

# Debitorka

## Introduction

The project was created to collect information about auctions
## Installation
- Clone repository by using command:
  ```
  $ git clone https://github.com/XoLeRyTeR/DadataFinder.git
  $ cd DadataFinder
  ```
- Create `.env` file in app root directory containing.
  It should look like this:
  ```
  PATH_DB=<path to database>
  ```
## Usage 
- Need download browser driver and move in project folder
- Specify the PATH_DIR_TEMP variable in the main file, pointing to the temporary folder.
```
  PATH_DIR_TEMP="<your path>/DadataFinder/data/temp"
  ```
## RUN
```
docker build --progress=plain -t cvcode_test .
python3 main_intagible.py --name_browser Firefox --temp_dir /app/data/temp/

  ```


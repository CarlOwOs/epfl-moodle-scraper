# epfl-moodle-scraper

A python script to scrape the files in your EPFL courses' Moodle page. The tequila session login based on [work by @antoinealb and @gcmalloc](https://github.com/antoinealb/python-tequila)

## Usage

First, write your EPFL Tequila username and password in a `.env` file with the variables `MOODLE_USERNAME` and `MOODLE_PASSWORD`

Next, you must add the course id and course name of the courses you wish to scrape in the `COURSE_ID_NAME_MAPPING` (which can easily be found from the course moodle URL).

You can run the script by specifying the course(s) you want to scrape from:

```
python moodle-scrape.py cs-450 ee-556
```

Or by not specifying any courses, in which cases all the courses in `COURSE_ID_NAME_MAPPING` will be scraped:

```
python moodle-scrape.py
```

## Personal recommendation

Write a shell script and add it to your `$PATH` so that you can run the script with a shorter command from any directory. 

Example shell script:

```
if [ "$1" == "pull" ]; then    
    echo "Scrapping from moodle..."
    python ~/path_to_script/moodle-scrape.py
    echo "All tasks completed."
else
    echo "Unknown command: $1"
    echo "Usage: q pull"
fi
```

Add the shell script (example `q`) to your path and reset the terminal. Then you should be able to scrape  by running `q pull` from anywhere. In Mac, this can be done with the following:

`chmod +x ~/path_to_shell_script/q`

`sudo ln -s ~/path_to_shell_scrupt/q /usr/local/bin/q`

## Warning

The folders created by the script should be treated as read-only. The script deletes the content in the input courses folders and downloads all the files in each course's Moodle page. Existing files, new files, and changes to files will be lost.

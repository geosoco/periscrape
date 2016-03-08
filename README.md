# Periscrape

A set of tools for finding periscope links within some Twitter streaming json files, then capturing the videos. This project is a research project to understand periscope usage during crisis events. Much of the ideas or information on accessing periscope was borrowed from the [Pyriscope](https://github.com/rharkanson/pyriscope). Additional information about the API came from [Gabriel G's periscope_api  documentation](https://github.com/gabrielg/periscope_api/blob/master/API.md). 

The process for running this is to first call `cull_periscope_links.py` . This takes two arguments, the first being a filename specifying the files to include (eg. `capture_*.json`). You may need to put this argument in quotes to prevent shell expansion. The second argument is the output csv file. The output will be 3 columns: id, url, text. The id being the tweet id, the url being the periscope.tv url, and the text being the tweet text.

The second setep will be `deduplicate_links.py`, which will keep only one version of each link it finds. This does not expand urls from link shorteners and other services, so it may not get all links duplicated. It replies on Twitter's expanded_url field having been mostly unwound (but this is not always the case, but usually the case for periscope links from the app).

Lastly, those CSVs need to be converted to flat text files containing just the urls. Each on its own line. Then you can run `scrape.py` which will download any finished stream that's available as well as the chat data. It takes two arguments `input file` and `output path`, and output is a directory. There's an optional `--procs` argument which specifies the number of processes to spawn for collecting in parallel. 

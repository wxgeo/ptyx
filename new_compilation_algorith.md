New compilation algorithm
=========================

Purpose
-------
Be able to provide a nice feedback about the percent of compiled documents compared to target.
This would be specially useful in GUI.

This is not so easy because much of the time, we expect all the versions of a documents
to have the same number of pages (which is default parameter).
So, we don't know for sure if a compiled document will be used at all.

Current algorithm
-----------------
Currently, enough documents are compiled to *potentially* reach the target, then the documents are analyzed,
to count their number of pages, and to select which documents to use according to actual options.

Then, if needed, more documents are compiled to reach the target.

Proposed new algorithm
----------------------
We should analyze documents after each compilation, to provide a feedback:

while (number of accepted documents) < target:
    for the n missing documents:
        - generate latex code
        - add a task to compile the latex code 
    for all the completed tasks (`concurrent.futures.as_completed(tasks)`):
        - analyze result 
        - call the given feedback function (if any), with the number of currently accepted documents

The callback functions can't be directly attached to futures, since the result of the future must be analyzed
first to determine if the new compiled document is accepted or not, depending on its number of pages.




# Tracing Commit Branch using Python

Imagine, you have two branch which one served as the base and the other one was where you code. Ideally, periodically, every code in the source branch (or feature branch) should be merged into the base and you can track the original commit source from git log.

However, you joined in the middle of the project, with multiple developer and the project had policies which made the base branch disconnected from other branch, the commits cannot be tracked. 

So these the scripts to help maintainer of the project to track commits, which commits of the source/feature branch had been merged into the base. 

Feature of the scripts:
1. Export commit data to csv format. Because sometimes you want to record it to spreadsheet;

2. Find closest commit between two branch, source and base. Before you can track the merged commits, you have to find out which commits of those two branch had close relationship.

3. Classify commits of branch source into three: merged to base, pending merge, and need manual review


I hope it's helpful. 


# Tracing Commit Branch using Python

Imagine, you have two branch which one served as the base and the other one was where you code. Ideally, periodically, every code in the source branch (or feature branch) should be merged into the base and you can track the original commit source from git log.

However, you joined in the middle of the project, with multiple developer and the project had policies which made the base branch disconnected from other branch, the commits cannot be tracked. 

So these the scripts to help maintainer of the project to track commits, which commits of the source/feature branch had been merged into the base. 

## Feature of the scripts:
1. Export commit data to csv format. Because sometimes you want to record it to spreadsheet;

2. Find closest commit between two branch, source and base. Before you can track the merged commits, you have to find out which commits of those two branch had close relationship.

3. Classify commits of branch source into three: merged to base, pending merge, and need manual review

## How to use

I usually start from opening a new sheet of spreadsheet. Then export the commit. 

```
git checkout feature
python script/export_git_log_to_csv.py 2025-12-01
```

And then trace the closest commits between two branch

```
python script/extract_commit.py find-closest feature main 2025-12-01
```

and you will have some result like these: 

> source_branch : feature
> base_branch   : main
> minimum_date  : 2025-12-01
>
> Closest pair:
>   source: c00297396415757cbceb00637031236b16af74a4 | 2026-02-10 07:40:51+00:00 | Pull request #326: hotfix: annoying feature
>   base  : e1c6bb74cff52edca6260775693e12c1dc8d33e4 | 2026-02-10 09:11:28+00:00 | Finally deployed for IN

After that you need the latest commit of both branch. 

```
git log -1 feature
git log -1 main
```

And then you run the classifying program

```
python extract_commit.py classify <source_closest> <source_latest> <base_closest> <base_latest> [threshold]
```

There is no perfect algorithm. Some commit were left behind so it was put into MANUAL REVIEW category. You should do tracking your self for example:

```
git checkout main
git diff <commit_from_source>^1 <commit_from_source>
git blame <the_modified_file>
```


I hope it's helpful. 


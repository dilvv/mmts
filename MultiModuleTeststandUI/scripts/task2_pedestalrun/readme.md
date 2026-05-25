`time sh run_single_module.sh`  ### takes around 15.2 second

If error happened, use
`sh step2.kria_env_setup.sh `
to reload firmware




### problems

The timeout checking procedure got
```
stat: cannot read file system information for '%z': No such file or directory
run_single_module.sh: line 101: [[: File: "log_testjob_daqclient.txt"
    ID: 1030300000000 Namelen: 255     Type: xfs
Block size: 4096       Fundamental block size: 4096
Blocks: Total: 119723401  Free: 90808638   Available: 90808638
Inodes: Total: 239563776  Free: 239177890: syntax error in expression (error token is ": "log_testjob_daqclient.txt"
    ID: 1030300000000 Namelen: 255     Type: xfs
Block size: 4096       Fundamental block size: 4096
Blocks: Total: 119723401  Free: 90808638   Available: 90808638
Inodes: Total: 239563776  Free: 239177890")
stat: cannot read file system information for '%z': No such file or directory
stat: cannot read file system information for '%z': No such file or directory
run_single_module.sh: line 101: [[: File: "log_testjob_daqclient.txt"
    ID: 1030300000000 Namelen: 255     Type: xfs
Block size: 4096       Fundamental block size: 4096
Blocks: Total: 119723401  Free: 90808491   Available: 90808491
Inodes: Total: 239563776  Free: 239177884: syntax error in expression (error token is ": "log_testjob_daqclient.txt"
    ID: 1030300000000 Namelen: 255     Type: xfs
Block size: 4096       Fundamental block size: 4096
Blocks: Total: 119723401  Free: 90808491   Available: 90808491
Inodes: Total: 239563776  Free: 239177884")
```


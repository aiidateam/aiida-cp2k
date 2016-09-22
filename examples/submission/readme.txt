To start testing the test_cp2k.py:

1. setup AiiDA 
2. setup and configure at least one computer in AiiDA, using
     verdi computer setup COMPUTERNAME
   followed by
     verdi computer configure COMPUTERNAME
3. setup cp2k code on that machine usiing
     verdi code setup
4. Run the test_cp2k.py file passing as a parameter the code label you chose in
   the code setup process.

Other tests work in a similar way.

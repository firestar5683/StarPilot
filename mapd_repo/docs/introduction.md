## What is mapd?
Mapd is a component for use in forks of comma.ai's
[openpilot](https://github.com/commaai/openpilot). It uses openstreetmap data to
provide speed limit and curve speed adjustments to the openpilot fork. Previous
openstreetmap integrations were written in python and used maps formatted for
routing programs. This resulted in huge map files when used offline, with some
US states requiring upwards of 50gb of data. The python code was also very cpu
and memory resource intensive which started to cause issues as openpilot became
more advanced and needed more of the available resources.

This mapd implementation aimed to fix those issues by moving to a more efficient
language (go) and by using custom map files generated off of openstreetmap
planet files. The result of this implementation was lowering memory usage from
30+% in some areas to sub 10% as well as cpu usage being reduced from using an
entire cpu core in some cases to a few percent of a core. The map files were
reduced from the entire planet needing over a terabyte of data and reducing it
to around 30gb of data total. It also introduced automatic weekly updates of the
entire planet on the server, which previously was only done manually and in
limited areas for other implementations. Finally, the hosting of the map files
has been cost optimized to cost only $5/month while delivering several terabytes
of map files to thousands of users across multiple openpilot forks every month.

Even with these massive benefits, there were some fairly major issues with the
implementation. Due to mapd being written in go, it was not able to use the
interprocess communication library that comma.ai made for openpilot. To overcome
this mapd just used the simpler persistent params implementation in openpilot
for interprocess communication by pointing it at memory backed file locations.
While this was functional, it was a blocking operation that as more data was
passed in and out of mapd could cause issues to the openpilot processes that
relied on the data. It also relied on data being read and then rewritten to
these parameters from the openpilot code to allow mapd to access the data it
needed. This meant any improvement that required more data from openpilot was a
breaking change for openpilot forks, slowing down feature enhancements for mapd.
Finally, and perhaps the largest issue, the data passed to and from mapd was not
contained in the standard openpilot logs. This made it incredibly difficult to
debug issues reported by users and also made some things like clip generators
impossible to work with mapd data.

## Introducing mapd v2.0
v2.x is a major rewrite of mapd to better integrate with openpilot forks. It
overcomes the interprocess communication issues of v1.x by now using the same
ipc interface as openpilot. This was accomplished by rewriting comma.ai's
[msgq](https://github.com/commaai/msgq) library in go. The go implementation can
be found [here](https://github.com/pfeiferj/gomsgq). This gives v2.x several
advantages in how it operates compared to v1.x:

* msgq is non-blocking. This means that mapd no longer causes unnecessary
  latency in the controls loop of openpilot.

* Mapd can now directly read openpilot's state. This means it no longer needs
  code added to openpilot to read and resend data to mapd.

* The mapd outputs can be stored in openpilot's log system. This means that the
  outputs can be replayed using the standard openpilot replay system giving
  several benefits:
    * clip generators that use the openpilot ui can now show the mapd based ui
    elements.
    * When debugging, the exact state of both openpilot and mapd can be seen in
    sync.
    * When debugging, a mapd instance can use the openpilot replay data as
    inputs. This enables checking if fixes for issues work by comparing how the
    new mapd instance behaves compared to the actual output of mapd on a device.

* Mapd now has more headroom in its ipc. This means that logic that previously
  was implemented on the python side of the openpilot fork can now be directly
  integrated into mapd itself. This should simplify the openpilot fork codebase
  and make it easier to maintain.

* Due to directly reading the openpilot state, mapd can now implement features
  that use additional data from openpilot without worrying about breaking
  compatiblity with forks.

* Mapd's update loop can now run faster and be more stateful as it now can
  actually know if the input data is new.

During the rewrite to use this new interprocess communication method, the
pros of this method were immediately beneficial. Many long standing bugs around
attaching to the current road in the data were resolved by debugging replay data.
Issues with distance calculations and deceleration triggering were also
identified and resolved. Predictions of upcoming path issues were identified and
resolved. Large parts of the codebase were able to be cleaned up due to having
more confidence that issues could be identified and fixed. Not only were these
issues found and resolved, but the scope of what mapd itself does was greatly
increased at the same time. The triggering logic for upcoming speeds is pulled
directly into mapd, including various methods of confirming and overriding the
upcoming speeds. Many more settings are now exposed as well to allow users to
customize behavior to their preferences. Even a non-map related functionality,
vision curve speed control, has been implemented directly into mapd (there's
plans to better integrate this with the map based curve speed control).

The improvements in v2.x are so numerous it makes me look back in wonder that
v1.x worked well for as many people as it did. Ultimately mapd v1.x was
something that was made for myself, but mapd v2.x is now something I can truly
say is made to support the openpilot fork community. I look forward to seeing
how much better this version works for users as it is deployed in your favorite
openpilot forks. v2.0.0 is just the start of many new and exciting features I
have planned for mapd, so stay tuned for more improvements in the future.

# Third-party notices

## MRR35 Hyundai angle and radar

The MRR35 radar generator and related Hyundai angle integration derive from the frozen StarPilot snapshot `678af783`, with relevant sunnypilot/opendbc angle-branch ancestry at `cc4b08625a98e94b318cab15e45e05dad58042bd`. Both upstream `LICENSE` and `LICENSE.md` were published for that source. Their scope is not unambiguous, so both applicable notices and the extension-file attribution are retained here without choosing between them. See [CREDITS.md](CREDITS.md) for the narrow source map.

### Upstream `opendbc` `LICENSE` notice (MIT)

Copyright (c) 2020, Comma.ai, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Upstream extension file notice

> Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.
>
> This file is part of sunnypilot and is licensed under the MIT License.
> See the LICENSE.md file in the root directory for more details.

### Upstream `LICENSE.md` notice (published as “Custom MIT License”)

The following notice is reproduced verbatim from the reference branch:

> # Custom MIT License
>
> Copyright (c) 2024, Haibin Wen, SUNNYPILOT LLC
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to view and modify the Software, subject to the following conditions:
>
> 1. **Permission Required**: Permission Required for Commercial, For-Profit, or Closed Source Use: Use of the Software, in whole or in part, for any commercial purposes, for-profit projects, or in closed source projects requires explicit written permission from the original author(s).
>
> 2. **Redistribution**: Any redistribution of the Software, modified or unmodified, must retain this license notice and the following acknowledgment:
>    "This software is licensed under a custom license requiring permission for use."
>
> 3. **Visibility**: Any project that uses the Software must visibly mention the following acknowledgment:
>    "This project uses software from Haibin Wen and SUNNYPILOT LLC and is licensed under a custom license requiring permission for use."
>
> 4. **No Warranty**: THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
>
> Contact sunnypilot Support <support@sunnypilot.ai> for permission requests.
>
> ---
>
> Haibin Wen, SUNNYPILOT LLC

Required upstream acknowledgments:

> This software is licensed under a custom license requiring permission for use.
>
> This project uses software from Haibin Wen and SUNNYPILOT LLC and is licensed under a custom license requiring permission for use.

For commercial, for-profit, or closed-source use, consult the upstream notice and obtain any
permission it requires. The upstream repository's simultaneous publication of two differently
scoped notices should be clarified with the relevant copyright holders before relying on one to
the exclusion of the other.

## BluePilot Ford support

The Ford lateral strategies, CAN constructors and native checks include work adapted from BluePilot's `bp-7.0` source, through StarPilot `2efe6017bfe14cee4807833e05f9a7f6ba255cdb`. See [CREDITS.md](CREDITS.md#ford-support-adapted-from-bluepilot) for contributors and source revisions. The upstream extension-file and `LICENSE.md` notices reproduced above also apply to the Ford extension sources; they are retained without resolving the difference between their published license descriptions.

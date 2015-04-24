.. _monitor-resolve-jobs:


########################
Monitor and resolve jobs
########################

Jobs are located in ``Connector > Queue > Jobs``.

A job is a unit of work for a single synchronization action.
Jobs are executed by the 'Workers'.

***
Q&A
***

My jobs are not executed, why?
==============================

The first thing to note is that the jobs are enqueued all the minutes.
Their execution is not immediate.

If you see no jobs executed in more than 1 minute, possibilities are:

1. Jobs are assigned to a worker which died. A worker
   can die when Odoo reloads his modules registry (after a module
   upgrade for instance). The dead workers are cleaned after 5 minutes,
   then the jobs are enqueued in a new one.

#. The jobs all have an ``eta`` (estimated time of arrival), so they
   will be executed later.

#. The scheduler action is not running, check in ``Settings > Scheduler
   > Scheduled Actions`` if the action ``Enqueue Jobs`` is active.

#. Odoo is running in multiprocess and it doesn't have a Cron Worker
   process running (when using Gunicorn).


A job is in state 'Failed', what should I do?
=============================================

The job encountered a problem.
Display the details of the job,
a section displays information about the exception.

The most comprehensible part of the error
is at the bottom of the error trace.
Sometimes, it proposes a resolution action.
Other times, you'll have to dive deeper to find the cause of the issue.
Anyway, once you think the issue should not happen anymore,
you can retry the job by clicking on ``Requeue``.

.. danger:: At any time, you can use the button ``Set to 'Done'``. This
            button will cancel the job. It should be used only if you
            really, really know what you are doing, because you may miss
            important synchronizations actions.


What happens if I shutdown the server when jobs are processing?
===============================================================

When jobs are interrupted, they won't commit any changes to the database
and will be restarted on the start of the Odoo server.

Note that the actions performed on Magento by a job could of course not
be reverted, so they will be done 2 times.


Why do I have a couple of Workers?
==================================

When Odoo is running in standalone (one process),
you'll always have 1 Jobs Worker.
When Odoo is running in multiprocess,
you'll have 1 Jobs Worker for each Odoo worker.

.. note:: To benefits of multiple workers, you need to:

          * have multiple Cron Workers (using the ``--max-cron-threads``
            option).
          * Copy the Scheduled Actions ``Enqueue Jobs`` as many times as
            you have Cron Workers.

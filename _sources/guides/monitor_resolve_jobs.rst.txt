.. _monitor-resolve-jobs:


########################
Monitor and resolve jobs
########################

Jobs are located in ``Queue > Jobs``.

A job is a unit of work for a single synchronization action.
Jobs are executed by the 'Workers'.

***
Q&A
***

My jobs are not executed, why?
==============================


#. The jobs all have an ``eta`` (estimated time of arrival), so they
   will be executed later.

#. The :ref:`Job runner <connector:jobrunner>` is not started or configured properly


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

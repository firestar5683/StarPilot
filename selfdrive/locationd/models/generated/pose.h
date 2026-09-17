#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_4115870174312830998);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_2299838754417090386);
void pose_H_mod_fun(double *state, double *out_652375008318869169);
void pose_f_fun(double *state, double dt, double *out_1837308153381576760);
void pose_F_fun(double *state, double dt, double *out_4411443613772384488);
void pose_h_4(double *state, double *unused, double *out_8735933422126784440);
void pose_H_4(double *state, double *unused, double *out_2621847070472080084);
void pose_h_10(double *state, double *unused, double *out_6171703416781276782);
void pose_H_10(double *state, double *unused, double *out_8600432860711518676);
void pose_h_13(double *state, double *unused, double *out_7399425647141855355);
void pose_H_13(double *state, double *unused, double *out_590426754860252717);
void pose_h_14(double *state, double *unused, double *out_7752950954395433666);
void pose_H_14(double *state, double *unused, double *out_1341393785867404445);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}
#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void pose_err_fun(double *nom_x, double *delta_x, double *out_1774761985787739244);
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_1588823582514134997);
void pose_H_mod_fun(double *state, double *out_6762725012352014604);
void pose_f_fun(double *state, double dt, double *out_2890023609994291477);
void pose_F_fun(double *state, double dt, double *out_6035160646602114178);
void pose_h_4(double *state, double *unused, double *out_8808099240894619749);
void pose_H_4(double *state, double *unused, double *out_4232559715645661926);
void pose_h_10(double *state, double *unused, double *out_7189369209365286749);
void pose_H_10(double *state, double *unused, double *out_569566124478173203);
void pose_h_13(double *state, double *unused, double *out_8915678619196498250);
void pose_H_13(double *state, double *unused, double *out_1020285890313329125);
void pose_h_14(double *state, double *unused, double *out_1817180151455941432);
void pose_H_14(double *state, double *unused, double *out_269318859306177397);
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt);
}
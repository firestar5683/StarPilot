#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_4576239672767356577);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_7162114440537636591);
void car_H_mod_fun(double *state, double *out_6671036100293030853);
void car_f_fun(double *state, double dt, double *out_937155241058689280);
void car_F_fun(double *state, double dt, double *out_6680942651904151339);
void car_h_25(double *state, double *unused, double *out_1771039490862882834);
void car_H_25(double *state, double *unused, double *out_1250301932680828952);
void car_h_24(double *state, double *unused, double *out_312253478356362907);
void car_H_24(double *state, double *unused, double *out_922347666324670614);
void car_h_30(double *state, double *unused, double *out_7811593157953647596);
void car_H_30(double *state, double *unused, double *out_3768634891188077579);
void car_h_26(double *state, double *unused, double *out_2809919890292801951);
void car_H_26(double *state, double *unused, double *out_2491201386193227272);
void car_h_27(double *state, double *unused, double *out_6592889242767479272);
void car_H_27(double *state, double *unused, double *out_5452157709247204157);
void car_h_29(double *state, double *unused, double *out_6868083305051985161);
void car_H_29(double *state, double *unused, double *out_2767163053132387062);
void car_h_28(double *state, double *unused, double *out_3988483921958781621);
void car_H_28(double *state, double *unused, double *out_803532781567060811);
void car_h_31(double *state, double *unused, double *out_2046233553147388723);
void car_H_31(double *state, double *unused, double *out_3117409488426578748);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}
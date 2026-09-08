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
void car_err_fun(double *nom_x, double *delta_x, double *out_789804740016769707);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_385986033898548509);
void car_H_mod_fun(double *state, double *out_4046004184415297016);
void car_f_fun(double *state, double dt, double *out_467921565295650481);
void car_F_fun(double *state, double dt, double *out_2429260194375294140);
void car_h_25(double *state, double *unused, double *out_4530459753918271082);
void car_H_25(double *state, double *unused, double *out_4551338626615593728);
void car_h_24(double *state, double *unused, double *out_211848015086222289);
void car_H_24(double *state, double *unused, double *out_7319833640502439787);
void car_h_30(double *state, double *unused, double *out_4687646422269400227);
void car_H_30(double *state, double *unused, double *out_4421999679472353658);
void car_h_26(double *state, double *unused, double *out_1875094318999546844);
void car_H_26(double *state, double *unused, double *out_809835307741537504);
void car_h_27(double *state, double *unused, double *out_8953904322109987302);
void car_H_27(double *state, double *unused, double *out_2247236367671928747);
void car_h_29(double *state, double *unused, double *out_5855390223345541964);
void car_H_29(double *state, double *unused, double *out_4932231023786745842);
void car_h_28(double *state, double *unused, double *out_8510755658264266202);
void car_H_28(double *state, double *unused, double *out_6895861295352072093);
void car_h_31(double *state, double *unused, double *out_3677036992164635768);
void car_H_31(double *state, double *unused, double *out_4581984588492554156);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}